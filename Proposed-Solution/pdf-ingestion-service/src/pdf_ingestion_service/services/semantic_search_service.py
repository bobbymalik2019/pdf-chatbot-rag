
import logging
import time
from uuid import UUID

from pdf_ingestion_service.persistence.semantic_search_repository import (
    SemanticSearchRepository,
)
from pdf_ingestion_service.services.knowledge_project_service import (
    KnowledgeProjectService,
)
from pdf_ingestion_service.embeddings.embedding_generator import (
    EmbeddingGenerator,
)

#importing the instances
from pdf_ingestion_service.config.settings import settings
from pdf_ingestion_service.dependencies import semantic_search_repository
from pdf_ingestion_service.services.knowledge_project_service import (
    project_service,
)
from pdf_ingestion_service.embeddings.ollama_embedding_generator import (
    OllamaEmbeddingGenerator,
)

logger = logging.getLogger(__name__)


class SemanticSearchService:

    def __init__(
        self,
        repository: SemanticSearchRepository,
        embedding_generator: EmbeddingGenerator,
        project_service: KnowledgeProjectService,
        embedding_model: str,
    ):
        self._repository = repository
        self._embedding_generator = embedding_generator
        self._project_service = project_service
        self._embedding_model = embedding_model

    def search(
        self,
        project_id: UUID,
        owner_id: UUID,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:

        query = query.strip()

        if not query:
            raise ValueError("Search query cannot be empty")

        if not 1 <= top_k <= 50:
            raise ValueError("top_k must be between 1 and 50")

        # Verify project existence and ownership before searching.
        # The existing service raises ProjectNotFoundError
        # for nonexistent or inaccessible projects.
        self._project_service.get_project(
            project_id=project_id,
            owner_id=owner_id,
        )

        start = time.perf_counter()

        logger.info(
            "SEMANTIC SEARCH START | project=%s | top_k=%d",
            project_id,
            top_k,
        )

        # Reuse the same embedding interface as ingestion.
        embeddings = self._embedding_generator.generate([query])

        if len(embeddings) != 1:
            raise ValueError(
                "Expected exactly one query embedding"
            )

        query_embedding = embeddings[0]

        if len(query_embedding) != 768:
            raise ValueError(
                "Query embedding must have 768 dimensions"
            )

        results = self._repository.search_similar_chunks(
            project_id=project_id,
            query_embedding=query_embedding,
            embedding_model=self._embedding_model,
            top_k=top_k,
        )

        logger.info(
            "SEMANTIC SEARCH COMPLETE | project=%s | matches=%d | duration=%.3fs",
            project_id,
            len(results),
            time.perf_counter() - start,
        )

        return results

semantic_search_service = SemanticSearchService(
    repository=semantic_search_repository,
    embedding_generator=OllamaEmbeddingGenerator(
        base_url=settings.ollama_base_url,
        model=settings.ollama_embedding_model,
    ),
    project_service=project_service,
    embedding_model=settings.ollama_embedding_model,
)    
