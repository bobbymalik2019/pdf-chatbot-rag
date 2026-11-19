
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from pdf_ingestion_service.dependencies import document_repository
from pdf_ingestion_service.services.knowledge_project_service import (
    project_service,
)
from pdf_ingestion_service.storage.pdf_storage_service import (
    pdf_storage_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/projects",
    tags=["Document Files"],
)


@router.get(
    "/{project_id}/documents/{document_id}/file"
)
def get_document_file(
    project_id: UUID,
    document_id: UUID,
):
    # Development identity only.
    # Replace with the existing authenticated identity
    # when authentication is integrated.
    owner_id = UUID(
        "52105c3d-ead8-4371-a2e8-f9d009452057"
    )

    # Verify project ownership.
    # Preserve the application's existing exception
    # handling for inaccessible projects.
    project_service.get_project(
        project_id=project_id,
        owner_id=owner_id,
    )

    document = document_repository.get_document(
        project_id=project_id,
        document_id=document_id,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    try:
        pdf_path = pdf_storage_service.get_path(
            document_id
        )
    except FileNotFoundError:
        logger.warning(
            "PDF FILE NOT FOUND | document_id=%s",
            document_id,
        )

        raise HTTPException(
            status_code=404,
            detail="Original PDF file not found",
        )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=document["filename"],
        content_disposition_type="inline",
    )
