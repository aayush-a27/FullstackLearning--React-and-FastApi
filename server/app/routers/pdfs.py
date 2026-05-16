from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.pdf import PdfResponse, PdfUploadResponse
from app.services.pdf_service import save_uploaded_pdf, get_user_pdfs, get_pdf_by_id, delete_pdf
from app.dependencies import get_current_user
from app.models.user import User
from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/pdfs", tags=["PDFs"])


@router.post("/upload", response_model=PdfUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF file."""
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed",
        )

    # Validate content type
    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Expected application/pdf",
        )

    # Check file size (read and check)
    content = await file.read()
    max_size = settings.MAX_PDF_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.MAX_PDF_SIZE_MB}MB",
        )

    # Reset file position after reading
    await file.seek(0)

    # Save the PDF
    pdf_doc = await save_uploaded_pdf(db, file, current_user.id)

    return PdfUploadResponse(
        id=pdf_doc.id,
        filename=pdf_doc.filename,
        file_size_bytes=pdf_doc.file_size_bytes,
        page_count=pdf_doc.page_count,
    )


@router.get("/", response_model=list[PdfResponse])
async def list_pdfs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all PDFs uploaded by the current user."""
    pdfs = await get_user_pdfs(db, current_user.id)
    return pdfs


@router.get("/{pdf_id}", response_model=PdfResponse)
async def get_pdf(
    pdf_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific PDF by ID."""
    pdf = await get_pdf_by_id(db, pdf_id, current_user.id)
    if not pdf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not found",
        )
    return pdf


@router.delete("/{pdf_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_pdf(
    pdf_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a PDF document and its file."""
    deleted = await delete_pdf(db, pdf_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not found",
        )
