from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.chat import ChatCreate, ChatUpdate, ChatResponse, ChatAttachPdf
from app.services.chat_service import (
    get_user_chats,
    get_chat_by_id,
    create_chat,
    delete_chat,
    update_chat,
    attach_pdf_to_chat,
)

router = APIRouter(prefix="/chats", tags=["Chats"])


@router.get("/", response_model=list[ChatResponse])
async def list_chats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all chats for the current user."""
    chats = await get_user_chats(db, current_user.id)
    return chats


@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_new_chat(
    data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session, optionally linking PDFs."""
    chat = await create_chat(
        db,
        user_id=current_user.id,
        title=data.title,
        pdf_ids=data.pdf_ids,
    )
    return chat


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific chat by ID."""
    chat = await get_chat_by_id(db, chat_id, current_user.id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )
    return chat


@router.patch("/{chat_id}", response_model=ChatResponse)
async def update_existing_chat(
    chat_id: UUID,
    data: ChatUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a chat's title, model, or smart switch setting."""
    update_data = data.model_dump(exclude_unset=True)
    chat = await update_chat(db, chat_id, current_user.id, **update_data)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )
    return chat


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_chat(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat and all its messages."""
    deleted = await delete_chat(db, chat_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )


@router.post("/{chat_id}/pdfs", response_model=ChatResponse)
async def attach_pdf(
    chat_id: UUID,
    data: ChatAttachPdf,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Attach an existing PDF to a chat."""
    chat = await attach_pdf_to_chat(db, chat_id, current_user.id, data.pdf_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat or PDF not found",
        )
    return chat
