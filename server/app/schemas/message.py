from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class MessageCreate(BaseModel):
    content: str
    model_id: str | None = None  # Optional — overrides selected model


class MessageResponse(BaseModel):
    id: UUID
    chat_id: UUID
    role: str
    content: str
    model_used: str | None = None
    metadata: dict | None = Field(None, validation_alias="metadata_")
    created_at: datetime

    model_config = {"from_attributes": True}
