import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.cache import chat_list_key, invalidate
from app.core.security import verify_password
from app.database import get_db
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    DeleteAccountRequest,
)
from app.dependencies import get_current_user
from app.models.user import User
from app.services.auth_service import get_user_by_username
from app.services.file_storage import delete_user_files

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get the current user's profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile."""
    update_data = updates.model_dump(exclude_unset=True)

    new_username = update_data.get("username")
    if new_username is not None and new_username != current_user.username:
        existing = await get_user_by_username(db, new_username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That username is already taken",
            )

    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    data: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently delete the account, its chats, messages and PDFs.
    The password is re-checked because this cannot be undone.
    """
    if not verify_password(data.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That password is incorrect.",
        )

    user_id = current_user.id
    await db.delete(current_user)  # chats, messages, PDFs cascade
    await db.flush()

    # Remove the user's uploaded files (object storage or local disk)
    await delete_user_files(user_id)

    await invalidate(chat_list_key(user_id))
    logger.info("Deleted account %s", user_id)
