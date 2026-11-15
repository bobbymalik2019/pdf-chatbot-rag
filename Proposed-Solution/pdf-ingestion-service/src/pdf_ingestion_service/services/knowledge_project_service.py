
from uuid import UUID
import logging


import psycopg

from pdf_ingestion_service.dependencies import (
    project_repository
)
from pdf_ingestion_service.persistence.knowledge_project_repository import (
    KnowledgeProjectRepository
)


logger = logging.getLogger(__name__)


class KnowledgeProjectError(Exception):
    """Base exception for Knowledge Project operations."""


class ProjectNotFoundError(KnowledgeProjectError):
    pass


class ProjectAlreadyExistsError(KnowledgeProjectError):
    pass


class ProjectValidationError(KnowledgeProjectError):
    pass


class ProjectOwnerNotFoundError(KnowledgeProjectError):
    pass


class KnowledgeProjectService:

    def __init__(
        self,
        repository: KnowledgeProjectRepository
    ):
        self.repository = repository

    def create_project(
        self,
        owner_id: UUID,
        name: str,
        description: str | None = None,
        tags: list[str] | None = None
    ) -> dict:

        # 1. Validate project name
        name = name.strip()

        if not name:
            raise ProjectValidationError(
                "Project name cannot be empty"
            )

        if len(name) > 255:
            raise ProjectValidationError(
                "Project name cannot exceed 255 characters"
            )

        # 2. Normalize optional fields
        if description is not None:
            description = description.strip()

        if tags is None:
            tags = []
        else:
            tags = list(dict.fromkeys(
                tag.strip()
                for tag in tags
                if tag.strip()
            ))

        # 3. Persist project
        try:
            project = self.repository.create_project(
                owner_id=owner_id,
                name=name,
                description=description,
                tags=tags
            )

        except psycopg.errors.UniqueViolation as exc:
            raise ProjectAlreadyExistsError(
                "A project with this name already exists"
            ) from exc

        except psycopg.errors.ForeignKeyViolation as exc:
            raise ProjectOwnerNotFoundError(
                "Project owner does not exist"
            ) from exc

        logger.info(
            "Knowledge project created | "
            "project_id=%s | owner_id=%s | name=%s",
            project["id"],
            owner_id,
            project["name"]
        )

        return project

    def get_project(
        self,
        project_id: UUID,
        owner_id: UUID
    ) -> dict:

        project = self.repository.get_project(
            project_id=project_id,
            owner_id=owner_id
        )

        if project is None:
            raise ProjectNotFoundError(
                "Knowledge Project not found"
            )

        return project

    def list_projects(
        self,
        owner_id: UUID
    ) -> list[dict]:

        return self.repository.list_projects(
            owner_id=owner_id
        )


project_service = KnowledgeProjectService(
    repository=project_repository
)