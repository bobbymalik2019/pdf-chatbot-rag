
from collections.abc import Callable
from uuid import UUID
import json

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from chat_history_service.persistence.database import (
    database_connection_factory,
)


class ChatMessageRepository:

    def __init__(
        self,
        connection_factory: Callable[[], Connection],
    ):
        self._connection_factory = connection_factory

    def save_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        sources: dict | list | None = None,
        status: str = "completed",
    ) -> dict:
        with self._connection_factory() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    INSERT INTO chat_messages
                        (conversation_id, role, content, sources, status)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        conversation_id,
                        role,
                        content,
                        Jsonb(sources) if sources is not None else None,
                        status,
                    ),
                )
                message = cursor.fetchone()

                cursor.execute(
                    """
                    UPDATE chat_conversations
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (conversation_id,),
                )

                return message

    def list_messages(
        self,
        conversation_id: UUID,
    ) -> list[dict]:
        with self._connection_factory() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM chat_messages
                    WHERE conversation_id = %s
                    ORDER BY created_at, id
                    """,
                    (conversation_id,),
                )
                return cursor.fetchall()

    def update_status(
        self,
        message_id: UUID,
        status: str,
    ) -> dict | None:
        with self._connection_factory() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    UPDATE chat_messages
                    SET status = %s
                    WHERE id = %s
                    RETURNING *
                    """,
                    (status, message_id),
                )
                return cursor.fetchone()


message_repository = ChatMessageRepository(
    connection_factory=database_connection_factory.get_connection
)
