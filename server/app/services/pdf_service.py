import uuid
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.pdf_document import PdfDocument
from app.services.file_storage import save_pdf, delete_pdf_file
import io
import pypdf


class InvalidPdfError(Exception):
    """Raised when an uploaded file can't be opened as a PDF."""


async def save_uploaded_pdf(
    db: AsyncSession,
    file: UploadFile,
    user_id: uuid.UUID,
) -> PdfDocument:
    """
    Store an uploaded PDF (R2 or local disk) and create its DB record.

    Only the page count is read here — text extraction, chunking and embedding
    happen in the background (app/services/pdf_processing.py) so large uploads
    return immediately instead of timing out the browser.
    """
    content = await file.read()

    # Validate before storing anything. Cheap: reads the page tree, not the pages.
    try:
        page_count = len(pypdf.PdfReader(io.BytesIO(content)).pages)
    except Exception as e:
        raise InvalidPdfError("This file isn't a readable PDF.") from e

    storage_path = await save_pdf(user_id, content)

    pdf_doc = PdfDocument(
        user_id=user_id,
        filename=file.filename,
        storage_path=storage_path,
        file_size_bytes=len(content),
        page_count=page_count,
        status="pending",
    )
    db.add(pdf_doc)
    await db.flush()
    await db.refresh(pdf_doc)
    return pdf_doc


async def get_user_pdfs(db: AsyncSession, user_id: uuid.UUID) -> list[PdfDocument]:
    """Get all PDFs uploaded by a user."""
    result = await db.execute(
        select(PdfDocument)
        .where(PdfDocument.user_id == user_id)
        .order_by(PdfDocument.uploaded_at.desc())
    )
    return list(result.scalars().all())


async def get_pdf_by_id(db: AsyncSession, pdf_id: uuid.UUID, user_id: uuid.UUID) -> PdfDocument | None:
    """Get a specific PDF by ID, ensuring it belongs to the user."""
    result = await db.execute(
        select(PdfDocument).where(
            PdfDocument.id == pdf_id,
            PdfDocument.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_pdf(db: AsyncSession, pdf_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Delete a PDF document and its file. Returns True if deleted."""
    pdf = await get_pdf_by_id(db, pdf_id, user_id)
    if not pdf:
        return False

    await delete_pdf_file(pdf.storage_path)
    await db.delete(pdf)
    return True

