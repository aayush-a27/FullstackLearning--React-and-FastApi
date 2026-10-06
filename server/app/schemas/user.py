from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date
from uuid import UUID


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str | None = None


class UserResponse(UserBase):
    id: UUID
    language: str | None = None
    purpose: str | None = None
    date_of_birth: date | None = None
    email_notifications: bool = False
    is_active: bool = True
    is_onboarded: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=255)
    username: str | None = Field(None, min_length=3, max_length=100, pattern=r"^\S+$")
    email_notifications: bool | None = None


class DeleteAccountRequest(BaseModel):
    """Deleting an account is irreversible, so the password is re-checked."""

    password: str


class OnboardingData(BaseModel):
    language: str
    purpose: str
    date_of_birth: str  # ISO date string "YYYY-MM-DD"
