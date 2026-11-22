#Will be responsible for coordinating the complete RAG answer workflow.
# Operation	           Responsibility
# Validate request	   Check project UUID, question, and retrieval limit
# Retrieve evidence	   Invoke existing project-scoped vector search
# Build context	       Call RAGContextBuilder
# Construct prompt	   Call RAGPromptBuilder
# Generate answer	   Call OllamaLLMClient
# Validate citations   Accept only markers present in the retrieved context
# Return response	   Provide answer, source metadata, model, and execution metrics

import logging
import re
import time
from uuid import UUID

from pdf_ingestion_service.models.rag_context import (
    RetrievedChunk,
    ContextSource
)

from pdf_ingestion_service.models.rag_answer import (
    RAGAnswerResponse
)
from pdf_ingestion_service.services.semantic_search_service import (
    SemanticSearchService,
    semantic_search_service
)
from pdf_ingestion_service.application.rag_context_builder import (
    RAGContextBuilder,
    rag_context_builder
)
from pdf_ingestion_service.application.rag_prompt_builder import (
    RAGPromptBuilder,
    rag_prompt_builder
)
# from pdf_ingestion_service.application.rag_context_builder import RAGContextBuilder
# from pdf_ingestion_service.application.rag_prompt_builder import RAGPromptBuilder
# from pdf_ingestion_service.llm import ollama_llm_client



from pdf_ingestion_service.llm.ollama_llm_client import (
    OllamaLLMClient,
    ollama_llm_client
)


logger = logging.getLogger(__name__)

# Temporary development identity
# DEV_OWNER_ID = UUID(
#     "52105c3d-ead8-4371-a2e8-f9d009452057"
# )
class RAGAnswerService:

    NO_ANSWER = (
        "The answer could not be found "
        "in the provided documents."
    )

    CITATION_PATTERN = re.compile(r"\[S\d+\]")

    def __init__(
        self,
        semantic_search_service: SemanticSearchService,
        context_builder: RAGContextBuilder,
        prompt_builder: RAGPromptBuilder,
        llm_client: OllamaLLMClient
    ):
        self._semantic_search_service = semantic_search_service
        self._context_builder = context_builder
        self._prompt_builder = prompt_builder
        self._llm_client = llm_client

    def answer(
        self,
        project_id: UUID,
        owner_id: UUID,
        question: str,
        top_k: int = 5
    ) -> RAGAnswerResponse:

        if not isinstance(project_id, UUID):
            raise ValueError("Invalid project_id")

        if not isinstance(owner_id, UUID):
            raise ValueError("Invalid owner_id")

        question = question.strip()

        if not question:
            raise ValueError("Question cannot be empty")

        if not 1 <= top_k <= 50:
            raise ValueError(
                "top_k must be between 1 and 50"
            )

        start = time.perf_counter()

        logger.info(
            "RAG ANSWER START | project=%s | top_k=%d",
            project_id,
            top_k
        )

        # 1. Existing semantic search includes
        # project ownership verification.
        search_results = self._semantic_search_service.search(
            project_id=project_id,
            owner_id=owner_id,
            query=question,
            top_k=top_k
        )

        # 2. Convert existing repository results
        # to the context builder's input model.
        chunks = [
            RetrievedChunk(
                chunk_id=result["chunk_id"],
                document_id=result["document_id"],
                filename=result["filename"],
                content=result["text"],
                page_number=result["start_page"],
                similarity_score=result["similarity"]
            )
            for result in search_results
        ]

        # 3. Build evidence context.
        context = self._context_builder.build(chunks)

        # 4. No usable context: do not call Ollama.
        if not context.sources:
            duration = time.perf_counter() - start

            logger.info(
                "RAG ANSWER NO CONTEXT | project=%s",
                project_id
            )

            return RAGAnswerResponse(
                project_id=project_id,
                question=question,
                answer=self.NO_ANSWER,
                sources=[],
                retrieved_chunks=len(chunks),
                included_chunks=0,
                context_truncated=context.truncated,
                duration_seconds=duration
            )

        # 5. Construct prompt.
        prompt = self._prompt_builder.build(
            question=question,
            context=context
        )

        # 6. Generate answer using Ollama.
        llm_response = self._llm_client.generate(
            prompt=prompt
        )

        # 7. Validate citation references.
        answer, verified_sources = self._validate_citations(
            answer=llm_response.answer,
            available_sources=context.sources
        )

        duration = time.perf_counter() - start

        logger.info(
            "RAG ANSWER COMPLETE | "
            "project=%s | retrieved=%d | "
            "included=%d | citations=%d | "
            "duration=%.2fs",
            project_id,
            len(chunks),
            context.included_chunks,
            len(verified_sources),
            duration
        )

        # 8. Return the final structured response.
        return RAGAnswerResponse(
            project_id=project_id,
            question=question,
            answer=answer,
            sources=verified_sources,
            retrieved_chunks=len(chunks),
            included_chunks=context.included_chunks,
            context_truncated=context.truncated,
            model=llm_response.model,
            prompt_tokens=llm_response.prompt_tokens,
            generated_tokens=llm_response.generated_tokens,
            duration_seconds=duration
        )

    def _validate_citations(
        self,
        answer: str,
        available_sources: list[ContextSource]
    ) -> tuple[str, list[ContextSource]]:

        source_lookup = {
            f"[{source.marker}]": source
            for source in available_sources
        }

        verified_sources = []
        seen = set()
        invalid_markers = set()

        def resolve_marker(match):
            marker = match.group(0)

            if marker not in source_lookup:
                invalid_markers.add(marker)
                return ""

            if marker not in seen:
                verified_sources.append(
                    source_lookup[marker]
                )
                seen.add(marker)

            return marker

        cleaned_answer = self.CITATION_PATTERN.sub(
            resolve_marker,
            answer
        ).strip()

        if invalid_markers:
            logger.warning(
                "RAG INVALID CITATIONS | markers=%s",
                sorted(invalid_markers)
            )

        return cleaned_answer, verified_sources


# Shared module-level instance
rag_answer_service = RAGAnswerService(
    semantic_search_service=semantic_search_service,
    context_builder=rag_context_builder,
    prompt_builder=rag_prompt_builder,
    llm_client=ollama_llm_client
)     