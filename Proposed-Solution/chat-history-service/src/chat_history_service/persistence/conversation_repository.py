
from collections.abc import Callable
from uuid import UUID

from psycopg import Connection
from psycopg.rows import dict_row

from chat_history_service.persistence.database import (
    database_connection_factory,
)


class ChatConversationRepository:

    def __init__(
        self,
        connection_factory: Callable[[], Connection],
    ):
        self._connection_factory = connection_factory

    def create(
        self,
        project_id: UUID,
        owner_id: str,
        title: str = "New Conversation",
    ) -> dict:
        with self._connection_factory() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    INSERT INTO chat_conversations (
                        project_id,
                        owner_id,
                        title
                    )
                    VALUES (%s, %s, %s)
                    RETURNING *
                    """,
                    (project_id, owner_id, title),
                )
                return cursor.fetchone()

    def get_by_id(
        self,
        conversation_id: UUID,
        owner_id: str,
    ) -> dict | None:
        with self._connection_factory() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM chat_conversations
                    WHERE id = %s
                      AND owner_id = %s
                    """,
                    (conversation_id, owner_id),
                )
                return cursor.fetchone()

    def list_by_project(
        self,
        project_id: UUID,
        owner_id: str,
    ) -> list[dict]:
        with self._connection_factory() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM chat_conversations
                    WHERE project_id = %s
                      AND owner_id = %s
                    ORDER BY updated_at DESC, id
                    """,
                    (project_id, owner_id),
                )
                return cursor.fetchall()

    def rename(
        self,
        conversation_id: UUID,
        owner_id: str,
        title: str,
    ) -> dict | None:
        with self._connection_factory() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    UPDATE chat_conversations
                    SET
                        title = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                      AND owner_id = %s
                    RETURNING *
                    """,
                    (title, conversation_id, owner_id),
                )
                return cursor.fetchone()

    def delete(
        self,
        conversation_id: UUID,
        owner_id: str,
    ) -> bool:
        with self._connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM chat_conversations
                    WHERE id = %s
                      AND owner_id = %s
                    """,
                    (conversation_id, owner_id),
                )
                return cursor.rowcount == 1


# Module-level repository instance
conversation_repository = ChatConversationRepository(
    connection_factory=database_connection_factory.get_connection
)
