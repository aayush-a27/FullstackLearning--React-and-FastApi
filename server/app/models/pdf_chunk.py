import uuid
from sqlalchemy import Integer, Text, LargeBinary, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class PdfChunk(Base):
    """
    One retrievable piece of a PDF, with its embedding.

    The embedding is stored as packed float32 bytes (not pgvector) because the
    embedding model returns 2048 dimensions, which is above pgvector's 2000-dim
    index limit — an index isn't possible either way, so similarity is computed
    in Python with numpy. See app/services/retrieval.py.
    """

    __tablename__ = "pdf_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pdf_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pdf_documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # 1-based page range this chunk came from
    page_start: Mapped[int] = mapped_column(Integer, default=1)
    page_end: Mapped[int] = mapped_column(Integer, default=1)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary)

    pdf = relationship("PdfDocument", back_populates="chunks")

    __table_args__ = (
        Index("ix_pdf_chunks_pdf_id_chunk_index", "pdf_id", "chunk_index"),
    )

    def __repr__(self):
        return f"<PdfChunk {self.chunk_index} of {self.pdf_id}>"
