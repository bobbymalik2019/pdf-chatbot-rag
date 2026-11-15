
import logging
from uuid import UUID


from pdf_ingestion_service.dependencies import document_repository
from pdf_ingestion_service.persistence.document_repository import DocumentRepository
from pdf_ingestion_service.services.knowledge_project_service import (
    KnowledgeProjectService,
    project_service,
)


logger = logging.getLogger(__name__)


class DocumentService:

    def __init__(self, repository:DocumentRepository,knowledge_project_service: KnowledgeProjectService,):
        self._repository = repository
        self._knowledge_project_service = knowledge_project_service

    def list_documents(self, project_id: UUID,owner_id: UUID) -> list[dict]:

        # Validate project existence and ownership first.
        # Raises ProjectNotFoundError if the project is not
        # accessible to this owner.
        self._knowledge_project_service.get_project(project_id=project_id,owner_id=owner_id)

        logger.info("LIST DOCUMENTS REQUEST | project_id=%s",project_id )

        documents = self._repository.list_documents( project_id=project_id)

        logger.info("LIST DOCUMENTS COMPLETE | project_id=%s | count=%d",project_id,len(documents))

        return documents



# Module-level shared service instance
document_service = DocumentService(
    repository=document_repository,
    knowledge_project_service=project_service
)
