import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship, deferred
from app.database import Base
from app.models.chat import chat_pdf_association


class PdfDocument(Base):
    __tablename__ = "pdf_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0)

    # Full text can be megabytes — deferred so loading a chat doesn't drag it along
    extracted_text: Mapped[str | None] = deferred(mapped_column(Text))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)

    # Background processing (text extraction -> chunking -> embeddings)
    # pending | processing | ready | failed
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    status_message: Mapped[str | None] = mapped_column(String(500))
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    # 0-100, so the UI can show a real progress bar while indexing
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Whole-document summary built from the section summaries
    # pending | processing | ready | failed
    summary_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    summary_progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary: Mapped[str | None] = deferred(mapped_column(Text))

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="pdf_documents")
    chats = relationship("Chat", secondary=chat_pdf_association, back_populates="pdf_documents")
    # passive_deletes lets Postgres' ON DELETE CASCADE do the work, instead of
    # SQLAlchemy loading every chunk row just to delete it one by one
    chunks = relationship(
        "PdfChunk", back_populates="pdf", cascade="all, delete-orphan", passive_deletes=True
    )
    sections = relationship(
        "PdfSection", back_populates="pdf", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self):
        return f"<PdfDocument {self.filename}>"
