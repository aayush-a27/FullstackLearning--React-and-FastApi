from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class ChatCreate(BaseModel):
    title: str = "New Chat"
    pdf_ids: list[UUID] = []


class ChatUpdate(BaseModel):
    title: str | None = None
    active_model: str | None = None
    smart_switch_enabled: bool | None = None


class ChatResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    active_model: str | None = None
    smart_switch_enabled: bool = True
    total_pdf_pages: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
