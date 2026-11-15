
import logging
import time
from uuid import UUID
from collections.abc import Callable

import numpy as np
from psycopg import Connection
from pgvector.psycopg import register_vector


logger = logging.getLogger(__name__)


class SemanticSearchRepository:

    def __init__(self, connection_factory: Callable[[], Connection]):
        self._connection_factory = connection_factory

    def search_similar_chunks(
        self,
        project_id: UUID,
        query_embedding: list[float],
        embedding_model: str,
        top_k: int = 5
    ) -> list[dict]:

        if len(query_embedding) != 768:
            raise ValueError(
                "Query embedding must have 768 dimensions"
            )

        if not 1 <= top_k <= 50:
            raise ValueError(
                "top_k must be between 1 and 50"
            )

        start = time.perf_counter()

        logger.info(
            "SEMANTIC SEARCH START | project=%s | model=%s | top_k=%d",
            project_id,
            embedding_model,
            top_k
        )

        vector = np.asarray(query_embedding, dtype=np.float32)

        with self._connection_factory() as conn:

            register_vector(conn)

            with conn.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        dc.id AS chunk_id,
                        dc.document_id,
                        d.filename,
                        dc.chunk_index,
                        dc.text,
                        dc.start_page,
                        dc.end_page,
                        1 - (dc.embedding <=> %s) AS similarity
                    FROM document_chunks dc
                    JOIN documents d
                        ON d.id = dc.document_id
                    WHERE d.project_id = %s
                      AND d.status = 'READY'
                      AND dc.embedding_model = %s
                    ORDER BY dc.embedding <=> %s
                    LIMIT %s
                    """,
                    (
                        vector,
                        project_id,
                        embedding_model,
                        vector,
                        top_k
                    )
                )

                columns = [
                    column.name
                    for column in cursor.description
                ]

                results = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]

        logger.info(
            "SEMANTIC SEARCH COMPLETE | project=%s | results=%d | duration=%.3fs",
            project_id,
            len(results),
            time.perf_counter() - start
        )

        return results
