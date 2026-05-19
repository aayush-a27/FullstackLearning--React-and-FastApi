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

    # Extract text and count pages using pypdf
    page_count = 1
    extracted_text = ""
    try:
        pdf_reader = pypdf.PdfReader(io.BytesIO(content))
        page_count = len(pdf_reader.pages)
        text_parts = []
        for page in pdf_reader.pages:
            text_parts.append(page.extract_text() or "")
        extracted_text = "\n".join(text_parts).strip()
    except Exception as e:
        extracted_text = f"[Error extracting PDF text: {str(e)}]"

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

