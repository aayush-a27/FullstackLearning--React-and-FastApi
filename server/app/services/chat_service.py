from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.chat import Chat
from app.models.pdf_document import PdfDocument


async def get_user_chats(db: AsyncSession, user_id: UUID) -> list[Chat]:
    """Get all chats for a user, ordered by most recent."""
    result = await db.execute(
        select(Chat)
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
        chat.pdf_documents = pdfs
        chat.total_pdf_pages = sum(p.page_count for p in pdfs)

    db.add(chat)
    await db.flush()
    await db.refresh(chat)
    return chat


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
    await db.refresh(chat)
    return chat
