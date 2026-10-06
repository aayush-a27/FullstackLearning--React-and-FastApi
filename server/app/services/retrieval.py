"""
Semantic search over a chat's PDF chunks.

Similarity is an exact cosine scan done with numpy rather than a pgvector index,
because the embedding model's 2048 dimensions exceed pgvector's 2000-dim index
limit — an index isn't possible either way at this dimensionality.
"""
import logging
from dataclasses import dataclass
from uuid import UUID
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.pdf_chunk import PdfChunk
from app.models.pdf_document import PdfDocument
from app.services.embedding_service import embed_query, unpack_matrix

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 8
# Chunks below this cosine score are dropped as irrelevant
MIN_SCORE = 0.15


@dataclass
class RetrievedChunk:
    chunk_id: UUID
    pdf_id: UUID
    filename: str
    page_start: int
    page_end: int
    content: str
    score: float


async def retrieve_chunks(
    db: AsyncSession,
    pdf_ids: list[UUID],
    question: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[RetrievedChunk]:
    """Return the chunks most relevant to `question` across the given PDFs."""
    if not pdf_ids:
        return []

    # Only ids + embeddings first — pulling every chunk's text would move
    # megabytes of content we're about to throw away.
    rows = (
        await db.execute(
            select(PdfChunk.id, PdfChunk.embedding)
            .where(PdfChunk.pdf_id.in_(pdf_ids), PdfChunk.embedding.is_not(None))
        )
    ).all()
    if not rows:
        return []

    query_vector = await embed_query(question)
    matrix = unpack_matrix([row.embedding for row in rows])
    if matrix.shape[1] != query_vector.shape[0]:
        logger.error(
            "Embedding dimension mismatch (stored %s, query %s) — re-upload the PDF",
            matrix.shape[1],
            query_vector.shape[0],
        )
        return []

    # Both sides are L2-normalized, so the dot product is the cosine similarity
    scores = matrix @ query_vector
    best = np.argsort(scores)[::-1][:top_k]
    selected = [(rows[i].id, float(scores[i])) for i in best if scores[i] >= MIN_SCORE]
    if not selected:
        return []

    score_by_id = dict(selected)
    detail_rows = (
        await db.execute(
            select(
                PdfChunk.id,
                PdfChunk.pdf_id,
                PdfChunk.page_start,
                PdfChunk.page_end,
                PdfChunk.content,
                PdfDocument.filename,
            )
            .join(PdfDocument, PdfDocument.id == PdfChunk.pdf_id)
            .where(PdfChunk.id.in_(list(score_by_id)))
        )
    ).all()

    results = [
        RetrievedChunk(
            chunk_id=row.id,
            pdf_id=row.pdf_id,
            filename=row.filename,
            page_start=row.page_start,
            page_end=row.page_end,
            content=row.content,
            score=score_by_id[row.id],
        )
        for row in detail_rows
    ]
    results.sort(key=lambda c: c.score, reverse=True)
    return results


def build_context(chunks: list[RetrievedChunk], max_chars: int) -> str:
    """Format retrieved chunks into prompt context, labelled for citation."""
    parts: list[str] = []
    used = 0
    for chunk in chunks:
        pages = (
            f"page {chunk.page_start}"
            if chunk.page_start == chunk.page_end
            else f"pages {chunk.page_start}-{chunk.page_end}"
        )
        block = f"[{chunk.filename}, {pages}]\n{chunk.content}"
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "\n\n---\n\n".join(parts)


def sources_from_chunks(chunks: list[RetrievedChunk]) -> list[dict]:
    """Compact, JSON-serializable source list for the message metadata."""
    seen: dict[tuple, dict] = {}
    for chunk in chunks:
        key = (str(chunk.pdf_id), chunk.page_start, chunk.page_end)
        if key not in seen:
            seen[key] = {
                "pdf_id": str(chunk.pdf_id),
                "filename": chunk.filename,
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
            }
    return list(seen.values())
