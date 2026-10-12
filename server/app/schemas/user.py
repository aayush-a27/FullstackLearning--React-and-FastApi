from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str | None = None


class UserResponse(UserBase):
    id: UUID
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=255)
    username: str | None = Field(None, min_length=3, max_length=100, pattern=r"^\S+$")


class DeleteAccountRequest(BaseModel):
    """Deleting an account is irreversible, so the password is re-checked."""

    password: str
