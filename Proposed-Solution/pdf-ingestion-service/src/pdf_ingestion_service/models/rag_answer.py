import logging
from uuid import UUID
from pydantic import BaseModel, Field
# from fastAPI import APIRouter, HTTPException

from pdf_ingestion_service.application.rag_context_builder import (
    ContextSource
)


logger = logging.getLogger(__name__)
class RAGAnswerResponse(BaseModel):
    project_id: UUID
    question: str
    answer: str

    sources: list[ContextSource] = Field(
        default_factory=list
    )

    retrieved_chunks: int = 0
    included_chunks: int = 0
    context_truncated: bool = False

    model: str | None = None
    prompt_tokens: int | None = None
    generated_tokens: int | None = None

    duration_seconds: float = 0.0

