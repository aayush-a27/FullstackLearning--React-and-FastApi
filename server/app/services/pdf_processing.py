"""
Background PDF pipeline: extract text -> chunk -> embed -> summarize.

Upload returns as soon as the file is on disk; everything expensive happens here
so the request doesn't block. Progress is tracked on PdfDocument.status and
PdfDocument.summary_status.
"""
import asyncio
import io
import logging
from uuid import UUID
import pypdf
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models.pdf_chunk import PdfChunk
from app.models.pdf_document import PdfDocument
from app.models.pdf_section import PdfSection
from app.services.ai_service import ai_service, AIServiceError
from app.services.chunking import chunk_pages, group_chunks_into_sections
from app.services.embedding_service import EmbeddingError, embed_texts, is_configured

logger = logging.getLogger(__name__)

# Rows inserted per flush while storing chunks
CHUNK_INSERT_BATCH = 500

# Characters of document text summarized per section
SECTION_TARGET_CHARS = 100_000
# Concurrent section summaries — kept low to stay within free-tier rate limits
SUMMARY_CONCURRENCY = 2
# Documents at or below this size are summarized in a single pass
SINGLE_PASS_SUMMARY_CHARS = 100_000

SECTION_INSTRUCTION = (
    "Summarize this section of a longer document in 150-250 words. "
    "Keep the specific facts, names, events and conclusions it contains."
)
COMBINE_INSTRUCTION = (
    "These are summaries of consecutive sections of one document, in order. "
    "Write a single coherent summary of the whole document in 300-500 words, "
    "covering the main narrative or argument from beginning to end."
)
WHOLE_DOC_INSTRUCTION = (
    "Summarize this document in 200-400 words, covering its purpose, main "
    "content and conclusions."
)

# Keep references so fire-and-forget tasks aren't garbage collected mid-run
_background_tasks: set[asyncio.Task] = set()


def schedule_processing(pdf_id: UUID):
    """Kick off processing for a PDF without blocking the caller."""
    task = asyncio.create_task(_run_pipeline(pdf_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _set_status(
    pdf_id: UUID,
    *,
    status: str | None = None,
    message: str | None = None,
    summary_status: str | None = None,
):
    """Update processing status in its own transaction so progress is visible."""
    values: dict = {}
    if status is not None:
        values["status"] = status
        values["status_message"] = message
    if summary_status is not None:
        values["summary_status"] = summary_status
    if not values:
        return
    async with AsyncSessionLocal() as db:
        await db.execute(update(PdfDocument).where(PdfDocument.id == pdf_id).values(**values))
        await db.commit()


class _ProgressReporter:
    """
    Writes a 0-100 progress value for one PDF, skipping tiny increments so a
    2,000-chunk document doesn't cause thousands of status writes.
    """

    MIN_STEP = 3

    def __init__(self, pdf_id: UUID, column: str):
        self.pdf_id = pdf_id
        self.column = column
        self.last = -1

    async def set(self, value: float, force: bool = False):
        value = max(0, min(100, int(value)))
        if not force and value - self.last < self.MIN_STEP:
            return
        self.last = value
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(PdfDocument)
                .where(PdfDocument.id == self.pdf_id)
                .values(**{self.column: value})
            )
            await db.commit()


def _extract_pages(path: str) -> list[str]:
    """Read per-page text from a PDF on disk (blocking — call via to_thread)."""
    with open(path, "rb") as f:
        content = f.read()
    reader = pypdf.PdfReader(io.BytesIO(content))
    return [(page.extract_text() or "") for page in reader.pages]


async def _run_pipeline(pdf_id: UUID):
    """Full pipeline for one PDF. Never raises — failures land in the status."""
    try:
        await _process_pdf(pdf_id)
    except Exception as e:
        logger.exception("PDF processing failed for %s", pdf_id)
        await _set_status(
            pdf_id,
            status="failed",
            message="We couldn't read this PDF. It may be scanned images or corrupted.",
            summary_status="failed",
        )
        return

    try:
        await _summarize_pdf(pdf_id)
    except Exception:
        logger.exception("PDF summarization failed for %s", pdf_id)
        await _set_status(pdf_id, summary_status="failed")


async def _process_pdf(pdf_id: UUID):
    """Extract text, chunk it, embed the chunks and store them."""
    async with AsyncSessionLocal() as db:
        pdf = await db.get(PdfDocument, pdf_id)
        if pdf is None:
            logger.warning("PDF %s vanished before processing", pdf_id)
            return
        storage_path = pdf.storage_path
        filename = pdf.filename

    await _set_status(pdf_id, status="processing", message=None)
    logger.info("Processing %s (%s)", filename, pdf_id)

    # Progress bands: reading 0-10%, embedding 10-95%, saving 95-100%
    progress = _ProgressReporter(pdf_id, "progress")
    await progress.set(2, force=True)

    pages = await asyncio.to_thread(_extract_pages, storage_path)
    full_text = "\n".join(pages).strip()
    await progress.set(10, force=True)

    if not full_text:
        await _set_status(
            pdf_id,
            status="failed",
            message="No text found in this PDF — it looks like scanned images.",
            summary_status="failed",
        )
        return

    chunks = chunk_pages(pages)
    logger.info("%s: %d pages -> %d chunks", filename, len(pages), len(chunks))

    embeddings: list[bytes | None] = [None] * len(chunks)
    embedding_note = None
    if is_configured():
        try:
            async def on_embed_progress(done: int, total: int):
                await progress.set(10 + 85 * done / max(total, 1))

            embeddings = list(
                await embed_texts(
                    [c.content for c in chunks], "passage", on_progress=on_embed_progress
                )
            )
        except EmbeddingError as e:
            logger.error("Embedding failed for %s: %s", pdf_id, e)
            embedding_note = "Search indexing is unavailable, so answers use the raw text."
    else:
        embedding_note = "No embedding key configured, so answers use the raw text."

    async with AsyncSessionLocal() as db:
        # Replace any chunks from a previous run
        existing = (
            await db.execute(select(PdfChunk.id).where(PdfChunk.pdf_id == pdf_id).limit(1))
        ).first()
        if existing:
            await db.execute(PdfChunk.__table__.delete().where(PdfChunk.pdf_id == pdf_id))

        for start in range(0, len(chunks), CHUNK_INSERT_BATCH):
            batch = chunks[start : start + CHUNK_INSERT_BATCH]
            db.add_all(
                [
                    PdfChunk(
                        pdf_id=pdf_id,
                        chunk_index=chunk.index,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        content=chunk.content,
                        embedding=embeddings[chunk.index],
                    )
                    for chunk in batch
                ]
            )
            await db.flush()

        await db.execute(
            update(PdfDocument)
            .where(PdfDocument.id == pdf_id)
            .values(
                extracted_text=full_text,
                page_count=len(pages),
                chunk_count=len(chunks),
                progress=100,
                status="ready",
                status_message=embedding_note,
            )
        )
        await db.commit()

    logger.info("%s ready: %d chunks indexed", filename, len(chunks))


async def _summarize_pdf(pdf_id: UUID):
    """Summarize the document section by section, then combine into one summary."""
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(PdfChunk.content, PdfChunk.page_start, PdfChunk.page_end)
                .where(PdfChunk.pdf_id == pdf_id)
                .order_by(PdfChunk.chunk_index)
            )
        ).all()
    if not rows:
        await _set_status(pdf_id, summary_status="failed")
        return

    await _set_status(pdf_id, summary_status="processing")
    summary_progress = _ProgressReporter(pdf_id, "summary_progress")
    await summary_progress.set(0, force=True)
    total_chars = sum(len(r.content) for r in rows)

    # Short documents don't need sectioning
    if total_chars <= SINGLE_PASS_SUMMARY_CHARS:
        text = "\n\n".join(r.content for r in rows)
        summary, _ = await ai_service.summarize_text(text, WHOLE_DOC_INSTRUCTION)
        await _store_summary(pdf_id, [], summary)
        return

    sections = group_chunks_into_sections(rows, SECTION_TARGET_CHARS)
    logger.info("Summarizing %s in %d sections (%d chars)", pdf_id, len(sections), total_chars)
    semaphore = asyncio.Semaphore(SUMMARY_CONCURRENCY)
    sections_done = 0

    async def summarize_section(index: int, section: list) -> tuple[int, int, int, str]:
        nonlocal sections_done
        text = "\n\n".join(chunk.content for chunk in section)
        try:
            async with semaphore:
                summary, _ = await ai_service.summarize_text(text, SECTION_INSTRUCTION)
        finally:
            # Sections are 90% of the work; combining them is the last 10%
            sections_done += 1
            await summary_progress.set(90 * sections_done / len(sections))
        return index, section[0].page_start, section[-1].page_end, summary

    results = await asyncio.gather(
        *(summarize_section(i, s) for i, s in enumerate(sections)),
        return_exceptions=True,
    )
    done = [r for r in results if not isinstance(r, BaseException)]
    if not done:
        raise AIServiceError("Every section summary failed")
    done.sort(key=lambda r: r[0])
    if len(done) < len(sections):
        logger.warning(
            "Only %d of %d sections summarized for %s", len(done), len(sections), pdf_id
        )

    combined = "\n\n".join(
        f"[pages {start}-{end}]\n{summary}" for _, start, end, summary in done
    )
    document_summary, _ = await ai_service.summarize_text(combined, COMBINE_INSTRUCTION)
    await _store_summary(pdf_id, done, document_summary)
    logger.info("Summary ready for %s", pdf_id)


async def _store_summary(pdf_id: UUID, sections: list[tuple], summary: str):
    async with AsyncSessionLocal() as db:
        await db.execute(PdfSection.__table__.delete().where(PdfSection.pdf_id == pdf_id))
        db.add_all(
            [
                PdfSection(
                    pdf_id=pdf_id,
                    section_index=index,
                    page_start=page_start,
                    page_end=page_end,
                    summary=text,
                )
                for index, page_start, page_end, text in sections
            ]
        )
        await db.execute(
            update(PdfDocument)
            .where(PdfDocument.id == pdf_id)
            .values(summary=summary, summary_status="ready", summary_progress=100)
        )
        await db.commit()


async def requeue_unfinished():
    """
    On startup, restart anything left mid-flight by a previous run.
    Without this a PDF interrupted by a restart would sit in 'processing' forever.
    """
    async with AsyncSessionLocal() as db:
        pending = (
            await db.execute(
                select(PdfDocument.id).where(
                    PdfDocument.status.in_(["pending", "processing"])
                )
            )
        ).scalars().all()
        stale_summaries = (
            await db.execute(
                select(PdfDocument.id).where(
                    PdfDocument.status == "ready",
                    PdfDocument.summary_status.in_(["pending", "processing"]),
                )
            )
        ).scalars().all()

    for pdf_id in pending:
        schedule_processing(pdf_id)
    for pdf_id in stale_summaries:
        task = asyncio.create_task(_resume_summary(pdf_id))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    if pending or stale_summaries:
        logger.info(
            "Requeued %d PDF(s) for processing and %d for summarization",
            len(pending),
            len(stale_summaries),
        )


async def _resume_summary(pdf_id: UUID):
    try:
        await _summarize_pdf(pdf_id)
    except Exception:
        logger.exception("Resuming summary failed for %s", pdf_id)
        await _set_status(pdf_id, summary_status="failed")
