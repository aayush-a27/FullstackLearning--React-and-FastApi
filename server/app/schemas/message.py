from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class MessageCreate(BaseModel):
    content: str
    model_id: str | None = None  # Optional — overrides selected model
    smart_switch: bool | None = None  # Optional — overrides the chat's smart switch setting
    # Edit / try again: a user message in this chat that this one replaces. It and
    # everything after it are dropped once the new answer is saved.
    replace_from_id: UUID | None = None


class MessageResponse(BaseModel):
    id: UUID
    chat_id: UUID
    role: str
    content: str
    model_used: str | None = None
    metadata: dict | None = Field(None, validation_alias="metadata_")
    created_at: datetime

    model_config = {"from_attributes": True}
