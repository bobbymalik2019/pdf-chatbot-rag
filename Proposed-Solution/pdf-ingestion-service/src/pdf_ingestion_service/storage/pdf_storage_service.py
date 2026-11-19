
import logging
from pathlib import Path
from uuid import UUID
from pdf_ingestion_service.config.settings import settings

logger = logging.getLogger(__name__)


class PDFStorageService:

    def __init__(self, storage_directory: Path):
        self.storage_directory = Path(storage_directory)
        self.storage_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(self, document_id: UUID, content: bytes) -> Path:
        if not content.startswith(b"%PDF-"):
            raise ValueError("Invalid PDF content")

        destination = self.get_destination(document_id)
        temporary = destination.with_suffix(".tmp")

        try:
            temporary.write_bytes(content)
            temporary.replace(destination)
        except OSError:
            temporary.unlink(missing_ok=True)
            logger.exception(
                "PDF STORAGE FAILED | document_id=%s",
                document_id,
            )
            raise

        logger.info(
            "PDF STORED | document_id=%s",
            document_id,
        )

        return destination
    
    def get_destination(self, document_id: UUID) -> Path:
        return self.storage_directory / f"{document_id}.pdf"
    
    def get_path(self, document_id: UUID) -> Path:
        path = self.storage_directory / f"{document_id}.pdf"

        if not path.is_file():
            raise FileNotFoundError(
                f"PDF not found for document {document_id}"
            )

        return path
    
    def delete(self, document_id: UUID) -> None:
        self.get_destination(document_id).unlink(
            missing_ok=True
        )

pdf_storage_service = PDFStorageService(
    storage_directory=settings.pdf_storage_path
)