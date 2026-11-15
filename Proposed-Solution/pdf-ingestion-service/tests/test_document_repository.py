import numpy as np
from pgvector.psycopg import register_vector

from uuid import uuid4
import psycopg
import pytest

from pdf_ingestion_service.config.settings import settings
from pdf_ingestion_service.persistence.database import (
    DatabaseConnectionFactory
)
from pdf_ingestion_service.models.chunk import DocumentChunk
from pdf_ingestion_service.persistence.document_repository import (
    DocumentRepository
)
from pdf_ingestion_service.dependencies import database_factory

#We reuse the existing factory while obtaining a fresh PostgreSQL connection for each test
#Previously I was using 
#with psycopg.connect(settings.database_url) as conn:
#    yield conn
#    conn.rollback()
#Psycopg's connection context manager automatically commits when the context exits successfully.
#If you want a test fixture that always rolls back uncommitted changes, explicitly managing the connection lifecycle is clearer:
#This ensures uncommitted changes are rolled back even if a test fails.
#One caveat: If the code being tested explicitly commits its transaction or opens another connection and commits, 
# this fixture cannot undo those changes. Our DocumentRepository currently creates its own connections, 
# so its successful inserts will remain committed unless the test explicitly cleans them up.
#For truly isolated repository integration tests, we'll eventually need transactional dependency injection or dedicated test-data cleanup.

@pytest.fixture
def db_connection():
    conn = database_factory.get_connection()

    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


@pytest.fixture
def test_project(db_connection):
    user_id = uuid4()
    project_id = uuid4()

    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO app_users (id, display_name)
            VALUES (%s, %s)
            """,
            (user_id, "Repository Test User")
        )

        cursor.execute(
            """
            INSERT INTO knowledge_projects (
                id, owner_id, name
            )
            VALUES (%s, %s, %s)
            """,
            (
                project_id,
                user_id,
                f"Repository Test {project_id}"
            )
        )

    # Repository uses a separate database connection,
    # so it needs committed fixture records.
    db_connection.commit()

    yield project_id

    # Clean up after the test.
    with db_connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM documents WHERE project_id = %s",
            (project_id,)
        )

        cursor.execute(
            "DELETE FROM knowledge_projects WHERE id = %s",
            (project_id,)
        )

        cursor.execute(
            "DELETE FROM app_users WHERE id = %s",
            (user_id,)
        )

    db_connection.commit()


@pytest.fixture
def repository():
    database_factory = DatabaseConnectionFactory(
        connection_string=settings.database_url
    )

    return DocumentRepository(
        connection_factory=database_factory.get_connection
    )


def create_chunks():
    return [
        DocumentChunk(
            chunk_index=0,
            text="Java supports object-oriented programming.",
            start_page=1,
            end_page=1
        ),
        DocumentChunk(
            chunk_index=1,
            text="Python supports multiple programming paradigms.",
            start_page=2,
            end_page=2
        )
    ]


def create_embeddings():
    return [
        [0.1] * 768,
        [0.2] * 768
    ]


def test_save_document(
    repository,
    test_project,
    db_connection
):
    document_id = repository.save_document(
        project_id=test_project,
        filename="programming.pdf",
        page_count=2,
        chunks=create_chunks(),
        embeddings=create_embeddings(),
        embedding_model="nomic-embed-text"
    )

    assert document_id is not None

    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT filename, page_count, status
            FROM documents
            WHERE id = %s
            """,
            (document_id,)
        )

        document = cursor.fetchone()

        assert document == (
            "programming.pdf",
            2,
            "READY"
        )

        cursor.execute(
            """
            SELECT chunk_index, text,
                   start_page, end_page,
                   vector_dims(embedding)
            FROM document_chunks
            WHERE document_id = %s
            ORDER BY chunk_index
            """,
            (document_id,)
        )

        rows = cursor.fetchall()

        assert len(rows) == 2

        assert rows[0][0] == 0
        assert rows[0][1] == (
            "Java supports object-oriented programming."
        )
        assert rows[0][2] == 1
        assert rows[0][3] == 1
        assert rows[0][4] == 768

        assert rows[1][0] == 1
        assert rows[1][4] == 768


def test_embedding_count_mismatch(
    repository,
    test_project,
    db_connection
):
    with pytest.raises(ValueError):
        repository.save_document(
            project_id=test_project,
            filename="invalid.pdf",
            page_count=2,
            chunks=create_chunks(),
            embeddings=[[0.1] * 768],
            embedding_model="nomic-embed-text"
        )

    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM documents
            WHERE project_id = %s
            """,
            (test_project,)
        )

        assert cursor.fetchone()[0] == 0


def test_transaction_rollback(
    repository,
    test_project,
    db_connection
):
    chunks = [
        DocumentChunk(
            chunk_index=0,
            text="First chunk",
            start_page=1,
            end_page=1
        ),
        DocumentChunk(
            chunk_index=0,
            text="Duplicate chunk index",
            start_page=1,
            end_page=1
        )
    ]

    with pytest.raises(psycopg.errors.UniqueViolation):
        repository.save_document(
            project_id=test_project,
            filename="rollback-test.pdf",
            page_count=1,
            chunks=chunks,
            embeddings=create_embeddings(),
            embedding_model="nomic-embed-text"
        )

    with db_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM documents
            WHERE project_id = %s
            """,
            (test_project,)
        )

        assert cursor.fetchone()[0] == 0
