from pydantic import BaseModel, EmailStr
from datetime import datetime, date
from uuid import UUID


class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str | None = None


class UserResponse(UserBase):
    id: UUID
    avatar_url: str | None = None
    language: str | None = None
    purpose: str | None = None
    date_of_birth: date | None = None
    is_active: bool = True
    is_onboarded: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: str | None = None
    username: str | None = None
    avatar_url: str | None = None


class OnboardingData(BaseModel):
    language: str
    purpose: str
    date_of_birth: str  # ISO date string "YYYY-MM-DD"
