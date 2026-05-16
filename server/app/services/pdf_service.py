import os
import uuid
from pathlib import Path
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.pdf_document import PdfDocument
from app.config import get_settings

settings = get_settings()


async def save_uploaded_pdf(
    db: AsyncSession,
    file: UploadFile,
    user_id: uuid.UUID,
) -> PdfDocument:
    """Save an uploaded PDF file to disk and create a DB record."""
    # Create upload directory if it doesn't exist
    upload_dir = Path(settings.UPLOAD_DIR) / str(user_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    file_ext = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = upload_dir / unique_filename

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Save to disk
    with open(file_path, "wb") as f:
        f.write(content)

    # Get page count (basic — count PDF pages from binary)
    page_count = _count_pdf_pages(content)

    # Extract text (placeholder — will use a proper PDF library later)
    extracted_text = ""  # TODO: Implement PDF text extraction

    # Create DB record
    pdf_doc = PdfDocument(
        user_id=user_id,
        filename=file.filename,
        storage_path=str(file_path),
        file_size_bytes=file_size,
        page_count=page_count,
        extracted_text=extracted_text,
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


def _count_pdf_pages(content: bytes) -> int:
    """Count pages in a PDF from its binary content (basic approach)."""
    try:
        # Count occurrences of "/Type /Page" (excluding "/Type /Pages")
        # This is a rough estimate; a proper library will be used later
        count = content.count(b"/Type /Page")
        pages_count = content.count(b"/Type /Pages")
        return max(count - pages_count, 1)
    except Exception:
        return 1
