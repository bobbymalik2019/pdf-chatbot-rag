import logging
from uuid import UUID
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from pdf_ingestion_service.application.rag_context_builder import (
    ContextSource
)


from pdf_ingestion_service.models.rag_answer_request import (
    RAGAnswerRequest
)
from pdf_ingestion_service.models.rag_answer import (
    RAGAnswerResponse
)
from pdf_ingestion_service.services.rag_answer_service import (
    rag_answer_service
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/projects",
    tags=["RAG Answers"]
)

# Temporary development identity.
# Replace with authenticated identity before deployment.
DEV_OWNER_ID = UUID(
    "52105c3d-ead8-4371-a2e8-f9d009452057"
)


@router.post(
    "/{project_id}/answer",
    response_model=RAGAnswerResponse
)
def answer_question(
    project_id: UUID,
    request: RAGAnswerRequest
) -> RAGAnswerResponse:

    logger.info(
        "RAG API REQUEST | project=%s | top_k=%d",
        project_id,
        request.top_k
    )

    try:
        return rag_answer_service.answer(
            project_id=project_id,
            owner_id=DEV_OWNER_ID,
            question=request.question,
            top_k=request.top_k
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc    