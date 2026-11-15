
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class RetrievedChunk(BaseModel):
    """Normalized input from the retrieval layer."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: int
    document_id: UUID
    filename: str = Field(min_length=1)
    content: str

    page_number: int | None = Field(
        default=None,
        ge=1
    )

    similarity_score: float | None = None


class ContextSource(BaseModel):
    """Metadata retained for citation verification."""

    marker: str
    chunk_id: int
    document_id: UUID
    filename: str
    page_number: int | None = None


class RAGContext(BaseModel):
    """Structured context for prompt construction."""

    context_text: str
    sources: list[ContextSource]

    included_chunks: int
    truncated: bool = False
