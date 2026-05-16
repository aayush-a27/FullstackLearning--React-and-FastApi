from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.schemas.message import MessageCreate, MessageResponse
from app.services.chat_service import get_chat_by_id
from app.services.ai_service import ai_service
from app.services.model_router import select_model
from app.dependencies import get_current_user
from app.models.user import User
from app.models.message import Message

router = APIRouter(prefix="/chats/{chat_id}/messages", tags=["Messages"])


@router.get("/", response_model=list[MessageResponse])
async def list_messages(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a chat, ordered chronologically."""
    # Verify chat belongs to user
    chat = await get_chat_by_id(db, chat_id, current_user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    chat_id: UUID,
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a user message and get an AI response.
    The AI model is selected based on smart switch or user preference.
    """
    # Verify chat belongs to user
    chat = await get_chat_by_id(db, chat_id, current_user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    # Save user message
    user_message = Message(
        chat_id=chat_id,
        role="user",
        content=data.content,
    )
    db.add(user_message)
    await db.flush()

    # Select AI model (smart switch or user choice)
    try:
        model_id = await select_model(
            question=data.content,
            user_selected_model=data.model_id or chat.active_model,
            smart_switch_enabled=chat.smart_switch_enabled,
        )
    except Exception:
        model_id = data.model_id or "gpt-4o-mini"

    # Gather PDF context
    pdf_context = ""
    if chat.pdf_documents:
        pdf_context = "\n\n---\n\n".join(
            doc.extracted_text or f"[PDF: {doc.filename} — text not yet extracted]"
            for doc in chat.pdf_documents
        )

    # Build message history for AI
    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
    )
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in result.scalars().all()
    ]

    # Get AI response
    ai_response_text = await ai_service.get_response(
        model_id=model_id,
        messages=history,
        pdf_context=pdf_context,
    )

    # Save AI response
    ai_message = Message(
        chat_id=chat_id,
        role="assistant",
        content=ai_response_text,
        model_used=model_id,
    )
    db.add(ai_message)
    await db.flush()
    await db.refresh(ai_message)

    return ai_message
