from uuid import UUID
from fastapi import APIRouter, HTTPException

from pdf_ingestion_service.models.knowledge_project import CreateProjectRequest
from pdf_ingestion_service.services.knowledge_project_service import (
    project_service,
    ProjectNotFoundError,
    ProjectAlreadyExistsError,
    ProjectOwnerNotFoundError,
    ProjectValidationError
)
from pdf_ingestion_service.services.document_service import document_service

from pdf_ingestion_service.models.semantic_search import (
    SemanticSearchRequest,
)
from pdf_ingestion_service.services.semantic_search_service import (
    semantic_search_service,
)

router = APIRouter(prefix="/api/v1/projects", tags=["Knowledge Projects"])




# Temporary development identity
DEV_OWNER_ID = UUID(
    "52105c3d-ead8-4371-a2e8-f9d009452057"
)


@router.post("", status_code=201)
def create_project(request: CreateProjectRequest):

    try:
        return project_service.create_project(
            owner_id=DEV_OWNER_ID,
            name=request.name,
            description=request.description,
            tags=request.tags
        )

    except ProjectAlreadyExistsError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc)
        ) from exc

    except ProjectOwnerNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        ) from exc

    except ProjectValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc)
        ) from exc


@router.get("")
def list_projects():

    return project_service.list_projects(
        owner_id=DEV_OWNER_ID
    )

print("UUID TYPE:", UUID)
print("UUID MODULE:", UUID.__module__)
@router.get("/{project_id}")
def get_project(project_id: UUID):

    try:
        return project_service.get_project(
            project_id=project_id,
            owner_id=DEV_OWNER_ID
        )

    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        ) from exc
DEV_USER_ID = "52105c3d-ead8-4371-a2e8-f9d009452057"
@router.get("/{project_id}/documents")
def list_project_documents(
    project_id: UUID
):
    try:
        return document_service.list_documents(
            project_id=project_id,
            owner_id=DEV_USER_ID
        )

    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        ) from exc



@router.post("/{project_id}/search")
def search_project_documents(project_id: UUID,request: SemanticSearchRequest,):
    try:
        results = semantic_search_service.search(
            project_id=project_id,
            owner_id=DEV_USER_ID,
            query=request.query,
            top_k=request.top_k,
        )

        return {
            "project_id": project_id,
            "query": request.query,
            "top_k": request.top_k,
            "results": results,
        }

    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
