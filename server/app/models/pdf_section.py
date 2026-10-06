import uuid
from sqlalchemy import Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class PdfSection(Base):
    """
    A summary of one slice of a PDF (roughly 100k characters).

    Whole-document questions ("summarize this book") can't be answered from a
    handful of retrieved chunks, so each section is summarized once in the
    background and those summaries are combined into the document summary.
    """

    __tablename__ = "pdf_sections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pdf_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pdf_documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    section_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int] = mapped_column(Integer, default=1)
    page_end: Mapped[int] = mapped_column(Integer, default=1)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    pdf = relationship("PdfDocument", back_populates="sections")

    def __repr__(self):
        return f"<PdfSection {self.section_index} of {self.pdf_id}>"
