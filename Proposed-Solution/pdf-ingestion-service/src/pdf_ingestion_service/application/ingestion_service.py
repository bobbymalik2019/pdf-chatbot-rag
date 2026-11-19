
import logging
import math
import time
from uuid import UUID
from uuid import uuid4
from pdf_ingestion_service.readers.content_reader import ContentReader

from pdf_ingestion_service.models.document import (
    ExtractedPage,
    IngestionResult
)
from pdf_ingestion_service.processing.text_normalizer import TextNormalizer
from pdf_ingestion_service.processing.document_chunker import DocumentChunker

from pdf_ingestion_service.embeddings.embedding_generator import (
    EmbeddingGenerator
)
from pdf_ingestion_service.persistence.document_repository import (
    DocumentRepository
)
from pdf_ingestion_service.storage.pdf_storage_service import (
    PDFStorageService,
)

logger = logging.getLogger(__name__)

class IngestionService:

    def __init__(self, reader: ContentReader, normalizer: TextNormalizer, chunker: DocumentChunker,
                         embedding_generator: EmbeddingGenerator,
                         document_repository: DocumentRepository,
                         embedding_model: str = "nomic-embed-text",
                         embedding_batch_size: int = 16,
                        pdf_storage_service: PDFStorageService | None = None, ):

        if embedding_batch_size <= 0:
            raise ValueError("embedding_batch_size must be positive")

        self.reader = reader
        self.normalizer = normalizer
        self.chunker = chunker
        self.embedding_generator = embedding_generator
        self.document_repository = document_repository
        self.embedding_model = embedding_model
        self.embedding_batch_size = embedding_batch_size
        self.pdf_storage_service = pdf_storage_service
    

    def ingest(
        self,
        filename: str,
        content: bytes,
        project_id: UUID
    ) -> IngestionResult:

        extracted_pages = self.reader.extract(content)
        logger.info("PDF EXTRACTION COMPLETE | pages=%d", len(extracted_pages))
        for page in extracted_pages:
            logger.info(
                "PAGE EXTRACTION | page=%d | raw_characters=%d",
                page.page_number,
                len(page.raw_text)
            )


        # Normalize each page
        normalized_pages = [
            ExtractedPage(
                page_number=page.page_number,
                raw_text=page.raw_text,
                normalized_text=self.normalizer.normalize(page.raw_text)
            )
            for page in extracted_pages
        ]

        logger.info(
            "NORMALIZATION COMPLETE | total_characters=%d",
            sum(len(page.normalized_text) for page in normalized_pages)
        )

        #Generate the chunks for the document  Validate and throw error if no usable text is found
        chunks = self.chunker.chunk(normalized_pages)
        logger.info("CHUNKING COMPLETE | chunks=%d", len(chunks))
        if not chunks:
            logger.warning(
                "INGESTION REJECTED | filename=%s | reason=no extractable text",
                filename
            )
            raise ValueError(
                "No usable text found in the PDF. "
                "The document may be scanned or image-based."
            )        

        #Generate embeddings in bounded batches
        embeddings: list[list[float]] = []

        total_batches = math.ceil(len(chunks) / self.embedding_batch_size)
        
        
        logger.info("EMBEDDING START | chunks=%d | batches=%d | batch_size=%d", len(chunks), total_batches, self.embedding_batch_size)
        for start in range(0,len(chunks),self.embedding_batch_size):
            batch_start = time.perf_counter()
            batch = chunks[start:start + self.embedding_batch_size]
            
            logger.info("EMBEDDING BATCH START | batch=%d/%d | chunks=%d-%d", start, total_batches, start + 1, start + len(batch))
            texts = [chunk.text for chunk in batch]
            batch_embeddings = self.embedding_generator.generate(texts)
            embeddings.extend(batch_embeddings)
            logger.info("EMBEDDING BATCH COMPLETE | batch=%d/%d | vectors=%d | duration=%.2fs", start, total_batches, len(batch_embeddings), time.perf_counter() - batch_start)

        logger.info("EMBEDDING COMPLETE | total_vectors=%d", len(embeddings))
        
        #Persist document, chunks, and embeddings
        document_id = uuid4()

        if self.pdf_storage_service is None:
            raise RuntimeError("PDF storage is not configured")

        # Save the original PDF before committing the
        # document as READY in PostgreSQL.
        self.pdf_storage_service.save(
            document_id=document_id,
            content=content,
        )

        try:
            self.document_repository.save_document(
                project_id=project_id,
                filename=filename,
                page_count=len(normalized_pages),
                chunks=chunks,
                embeddings=embeddings,
                embedding_model=self.embedding_model,
                document_id=document_id,
            )

        except Exception:
            logger.exception(
                "DOCUMENT PERSISTENCE FAILED | document_id=%s",
                document_id,
            )

            try:
                self.pdf_storage_service.delete(document_id)
            except OSError:
                logger.exception(
                    "PDF CLEANUP FAILED | document_id=%s",
                    document_id,
                )

            raise

        return IngestionResult(
            document_id=document_id,
            filename=filename,
            status="EXTRACTED",
            page_count=len(normalized_pages),
            pages=normalized_pages,
            chunks=chunks
        )
