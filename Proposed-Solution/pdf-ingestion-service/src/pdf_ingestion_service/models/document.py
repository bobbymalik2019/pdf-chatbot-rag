from uuid import UUID
from pydantic import BaseModel, Field
from pdf_ingestion_service.models.chunk import DocumentChunk


class ExtractedPage(BaseModel):
    page_number: int = Field( ge= 1)
    raw_text: str
    normalized_text: str


class IngestionResult(BaseModel):
    document_id: UUID | None = None,
    filename: str
    status: str
    page_count: int
    pages: list[ExtractedPage]
    chunks: list[DocumentChunk] = Field(default_factory=list)
