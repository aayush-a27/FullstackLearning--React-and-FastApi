from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.chat import Chat
from app.models.pdf_document import PdfDocument

# Multi-PDF limits per chat (mirrors PDF_LIMITS in client/src/utils/constants.js)
SMALL_PDF_MAX_PAGES = 5
MEDIUM_PDF_MAX_PAGES = 30
SMALL_PDF_MAX_FILES = 5
MEDIUM_PDF_MAX_FILES = 2
LARGE_PDF_MAX_FILES = 1


class PdfLimitError(Exception):
    """Raised when attaching PDFs would exceed the per-chat limit."""


def max_pdfs_allowed(page_counts: list[int]) -> int:
    """
    All PDFs <= 5 pages -> up to 5; any PDF 6-30 pages -> up to 2;
    any PDF > 30 pages -> only 1.
    """
    largest = max(page_counts, default=0)
    if largest > MEDIUM_PDF_MAX_PAGES:
        return LARGE_PDF_MAX_FILES
    if largest > SMALL_PDF_MAX_PAGES:
        return MEDIUM_PDF_MAX_FILES
    return SMALL_PDF_MAX_FILES


def check_pdf_limit(pdfs: list[PdfDocument]):
    """Raise PdfLimitError if this set of PDFs is too many for one chat."""
    allowed = max_pdfs_allowed([p.page_count for p in pdfs])
    if len(pdfs) > allowed:
        raise PdfLimitError(
            f"This chat can hold at most {allowed} PDF{'s' if allowed > 1 else ''} "
            "of this size. Start a new chat for more documents."
        )


async def get_user_chats(db: AsyncSession, user_id: UUID) -> list[Chat]:
    """Get all chats for a user, ordered by most recent."""
    result = await db.execute(
        select(Chat)
        .options(selectinload(Chat.pdf_documents))
        .where(Chat.user_id == user_id)
        .order_by(Chat.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_chat_by_id(db: AsyncSession, chat_id: UUID, user_id: UUID) -> Chat | None:
    """Get a specific chat by ID, ensuring it belongs to the user."""
    result = await db.execute(
        select(Chat)
        .options(selectinload(Chat.pdf_documents))
        .where(Chat.id == chat_id, Chat.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_chat(
    db: AsyncSession,
    user_id: UUID,
    title: str = "New Chat",
    pdf_ids: list[UUID] | None = None,
) -> Chat:
    """Create a new chat session, optionally linking PDFs."""
    chat = Chat(user_id=user_id, title=title)

    if pdf_ids:
        # Fetch PDFs and attach them
        result = await db.execute(
            select(PdfDocument).where(
                PdfDocument.id.in_(pdf_ids),
                PdfDocument.user_id == user_id,
            )
        )
        pdfs = list(result.scalars().all())
        check_pdf_limit(pdfs)
        chat.pdf_documents = pdfs
        chat.total_pdf_pages = sum(p.page_count for p in pdfs)

    db.add(chat)
    await db.flush()
    return await get_chat_by_id(db, chat.id, user_id)


async def delete_chat(db: AsyncSession, chat_id: UUID, user_id: UUID) -> bool:
    """Delete a chat session. Returns True if deleted."""
    chat = await get_chat_by_id(db, chat_id, user_id)
    if not chat:
        return False
    await db.delete(chat)
    return True


async def update_chat(db: AsyncSession, chat_id: UUID, user_id: UUID, **kwargs) -> Chat | None:
    """Update chat attributes."""
    chat = await get_chat_by_id(db, chat_id, user_id)
    if not chat:
        return None
    for key, value in kwargs.items():
        if value is not None and hasattr(chat, key):
            setattr(chat, key, value)
    await db.flush()
    return await get_chat_by_id(db, chat_id, user_id)


async def attach_pdf_to_chat(db: AsyncSession, chat_id: UUID, user_id: UUID, pdf_id: UUID) -> Chat | None:
    """Attach an existing PDF to a chat."""
    chat = await get_chat_by_id(db, chat_id, user_id)
    if not chat:
        return None
    
    # Fetch PDF
    result = await db.execute(
        select(PdfDocument).where(
            PdfDocument.id == pdf_id,
            PdfDocument.user_id == user_id,
        )
    )
    pdf = result.scalar_one_or_none()
    if not pdf:
        return None

    # Check if already attached
    if not any(p.id == pdf_id for p in chat.pdf_documents):
        check_pdf_limit(chat.pdf_documents + [pdf])
        chat.pdf_documents.append(pdf)
        chat.total_pdf_pages = sum(p.page_count for p in chat.pdf_documents)
        await db.flush()
        
    return await get_chat_by_id(db, chat_id, user_id)
