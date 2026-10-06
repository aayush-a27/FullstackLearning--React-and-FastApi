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

    # Background processing state
    status: str = "ready"            # pending | processing | ready | failed
    status_message: str | None = None
    chunk_count: int = 0
    progress: int = 0                # 0-100 while indexing
    summary_status: str = "pending"  # pending | processing | ready | failed
    summary_progress: int = 0        # 0-100 while the summary is written

    model_config = {"from_attributes": True}


class PdfUploadResponse(BaseModel):
    id: UUID
    filename: str
    file_size_bytes: int
    page_count: int
    status: str = "pending"
    message: str = "PDF uploaded — indexing it now"
