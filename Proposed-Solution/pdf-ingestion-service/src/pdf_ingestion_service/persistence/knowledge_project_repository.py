import logging
from collections.abc import Callable
from uuid import UUID

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row


logger = logging.getLogger(__name__)


class KnowledgeProjectRepository:

    def __init__(
        self,
        connection_factory: Callable[[], Connection]
    ):
        self._connection_factory = connection_factory

    def create_project(
        self,
        owner_id: UUID,
        name: str,
        description: str | None = None,
        tags: list[str] | None = None
    ) -> dict:

        sql = """
            INSERT INTO knowledge_projects
                (owner_id, name, description, tags)
            VALUES
                (%s, %s, %s, %s)
            RETURNING
                id,
                owner_id,
                name,
                description,
                tags,
                created_at,
                updated_at
        """

        with self._connection_factory() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    sql,
                    (
                        owner_id,
                        name,
                        description,
                        tags if tags is not None else []
                    )
                )

                project = cursor.fetchone()

        logger.info(
            "Knowledge project created | "
            "project_id=%s | owner_id=%s",
            project["id"],
            owner_id
        )

        return project

    def get_project(
        self,
        project_id: UUID,
        owner_id: UUID
    ) -> dict | None:

        sql = """
            SELECT
                id,
                owner_id,
                name,
                description,
                tags,
                created_at,
                updated_at
            FROM knowledge_projects
            WHERE id = %s
              AND owner_id = %s
        """

        with self._connection_factory() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(sql, (project_id, owner_id))
                return cursor.fetchone()

    def list_projects(
        self,
        owner_id: UUID
    ) -> list[dict]:

        sql = """
            SELECT
                id,
                owner_id,
                name,
                description,
                tags,
                created_at,
                updated_at
            FROM knowledge_projects
            WHERE owner_id = %s
            ORDER BY created_at DESC, id DESC
        """

        with self._connection_factory() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(sql, (owner_id,))
                return cursor.fetchall()