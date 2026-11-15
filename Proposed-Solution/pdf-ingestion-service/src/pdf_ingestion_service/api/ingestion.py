from uuid import UUID
from fastapi import Form
import pymupdf
from fastapi import APIRouter, File, UploadFile, HTTPException

from pdf_ingestion_service.application.ingestion_service import IngestionService
from pdf_ingestion_service.processing.document_chunker import DocumentChunker
from pdf_ingestion_service.readers.pdf_content_reader import PDFContentReader
from pdf_ingestion_service.models.document import IngestionResult
from pdf_ingestion_service.processing.text_normalizer import TextNormalizer


from pdf_ingestion_service.config.settings import Settings
from pdf_ingestion_service.embeddings.ollama_embedding_generator import (
    OllamaEmbeddingGenerator
)
# from pdf_ingestion_service.persistence.document_repository import (
#     document_repository
# )
from pdf_ingestion_service.dependencies import document_repository

from pdf_ingestion_service.dependencies import document_repository
from pdf_ingestion_service.config.settings import settings

router = APIRouter(
    prefix="/api/v1/ingestions",
    tags=["PDF Ingestion"]
)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

#settings = Settings()

# Create the service and inject the reader
ingestion_service = IngestionService(
    reader=PDFContentReader(),
    normalizer=TextNormalizer(),
    chunker=DocumentChunker(chunk_size=1000,chunk_overlap=200),
    embedding_generator=OllamaEmbeddingGenerator(base_url=settings.ollama_base_url,
                                                model=settings.ollama_embedding_model),
    document_repository=document_repository,
    embedding_model=settings.ollama_embedding_model,
    embedding_batch_size=16
)

@router.post("")
async def upload_pdf(file: UploadFile = File(...), project_id: UUID = Form(...)):

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    # Read at most 20 MB + 1 byte to enforce the limit
    content = await file.read(MAX_FILE_SIZE + 1)

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="PDF exceeds the 20 MB limit"
        )

    # Basic PDF signature validation
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file"
        )

    reader = PDFContentReader()
    try:
        result = ingestion_service.ingest(filename=file.filename,content=content,project_id=project_id )
        return result
    except (pymupdf.FileDataError, pymupdf.EmptyFileError, ValueError   ) as exc:
        raise HTTPException(status_code=422,detail="Unable to extract text from PDF") from exc
