from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class PdfResponse(BaseModel):
    id: UUID
    user_id: UUID
    filename: str
    file_size_bytes: int
    page_count: int
    uploaded_at: datetime
    metadata: dict | None = Field(None, validation_alias="metadata_")

    model_config = {"from_attributes": True}


class PdfUploadResponse(BaseModel):
    id: UUID
    filename: str
    file_size_bytes: int
    page_count: int
    message: str = "PDF uploaded successfully"
