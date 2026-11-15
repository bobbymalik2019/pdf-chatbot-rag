
import logging
import time
from uuid import UUID
import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from collections.abc import Callable
from psycopg import Connection

from pdf_ingestion_service.models.chunk import DocumentChunk

logger = logging.getLogger(__name__)
class DocumentRepository:

    def __init__(self, connection_factory: Callable[[], Connection]):
        self._connection_factory = connection_factory

    def save_document(
        self,
        project_id: UUID,
        filename: str,
        page_count: int,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        embedding_model: str
    ) -> UUID:

        if len(chunks) != len(embeddings):
            raise ValueError(
                "Number of chunks must match number of embeddings"
            )

        if any(len(vector) != 768 for vector in embeddings):
            raise ValueError(
                "Every embedding must have 768 dimensions"
            )

        db_start = time.perf_counter()
        logger.info("DB TRANSACTION START | project=%s | filename=%s | chunks=%d",project_id,filename,len(chunks))

        with  self._connection_factory() as conn:
            
            register_vector(conn)

            with conn.cursor() as cursor:

                cursor.execute(
                    """
                    INSERT INTO documents (
                        project_id,
                        filename,
                        page_count,
                        status
                    )
                    VALUES (%s, %s, %s, 'READY')
                    RETURNING id
                    """,
                    (project_id, filename, page_count)
                )

                document_id = cursor.fetchone()[0]

                for chunk, embedding in zip(chunks, embeddings):

                    cursor.execute(
                        """
                        INSERT INTO document_chunks (
                            document_id,
                            chunk_index,
                            text,
                            start_page,
                            end_page,
                            embedding,
                            embedding_model
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            document_id,
                            chunk.chunk_index,
                            chunk.text,
                            chunk.start_page,
                            chunk.end_page,
                            np.asarray(embedding, dtype=np.float32),
                            embedding_model
                        )
                    )

        logger.info("DB TRANSACTION COMMITTED | document_id=%s | duration=%.2fs",document_id,time.perf_counter() - db_start)
        return document_id


    def list_documents(self, project_id: UUID) -> list[dict]:
        logger.info(
            "FETCH PROJECT DOCUMENTS | project_id=%s",
            project_id
        )

        with self._connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        project_id,
                        filename,
                        page_count,
                        status,
                        uploaded_at
                    FROM documents
                    WHERE project_id = %s
                    ORDER BY uploaded_at DESC, id DESC
                    """,
                    (project_id,)
                )

                columns = [
                    column.name
                    for column in cursor.description
                ]

                documents = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]

        logger.info(
            "FETCH PROJECT DOCUMENTS COMPLETE | project_id=%s | count=%d",
            project_id,
            len(documents)
        )

        return documents

