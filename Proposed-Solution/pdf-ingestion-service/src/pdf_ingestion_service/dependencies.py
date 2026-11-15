from pdf_ingestion_service.config.settings import settings  #importing the settings instance directly from the settings module

from pdf_ingestion_service.persistence.database import (
    DatabaseConnectionFactory
)

from pdf_ingestion_service.persistence.document_repository import (
    DocumentRepository
)

from pdf_ingestion_service.persistence.knowledge_project_repository import (
    KnowledgeProjectRepository
)

from pdf_ingestion_service.persistence.semantic_search_repository import (
    SemanticSearchRepository
)

database_factory = DatabaseConnectionFactory(
    connection_string=settings.database_url
)

document_repository = DocumentRepository(
    connection_factory=database_factory.get_connection
)

project_repository = KnowledgeProjectRepository(
    connection_factory=database_factory.get_connection
)

semantic_search_repository = SemanticSearchRepository(
    connection_factory=database_factory.get_connection
)
