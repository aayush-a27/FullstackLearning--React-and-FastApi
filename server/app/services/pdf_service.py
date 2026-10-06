import os
import uuid
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.pdf_document import PdfDocument
from app.config import get_settings
import io
import pypdf

settings = get_settings()


class InvalidPdfError(Exception):
    """Raised when an uploaded file can't be opened as a PDF."""


async def save_uploaded_pdf(
    db: AsyncSession,
    file: UploadFile,
    user_id: uuid.UUID,
) -> PdfDocument:
    """
    Save an uploaded PDF to disk and create its DB record.

    Only the page count is read here — text extraction, chunking and embedding
    happen in the background (app/services/pdf_processing.py) so large uploads
    return immediately instead of timing out the browser.
    """
    upload_dir = Path(settings.UPLOAD_DIR) / str(user_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_ext = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = upload_dir / unique_filename

    content = await file.read()
    file_size = len(content)

    with open(file_path, "wb") as f:
        f.write(content)

    # Cheap: reads the page tree, not the page contents
    try:
        page_count = len(pypdf.PdfReader(io.BytesIO(content)).pages)
    except Exception as e:
        os.remove(file_path)
        raise InvalidPdfError("This file isn't a readable PDF.") from e

    pdf_doc = PdfDocument(
        user_id=user_id,
        filename=file.filename,
        storage_path=str(file_path),
        file_size_bytes=file_size,
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

    # Delete file from disk
    try:
        os.remove(pdf.storage_path)
    except OSError:
        pass

    await db.delete(pdf)
    return True

