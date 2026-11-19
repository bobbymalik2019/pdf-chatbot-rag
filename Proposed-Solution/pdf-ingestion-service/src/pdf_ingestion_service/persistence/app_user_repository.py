
from collections.abc import Callable

from psycopg import Connection
from psycopg.rows import dict_row


class AppUserRepository:

    def __init__(
        self,
        connection_factory: Callable[[], Connection],
    ):
        self._connection_factory = connection_factory

    def find_by_external_user_id(
        self,
        external_user_id: str,
    ) -> dict | None:

        sql = """
            SELECT
                id,
                external_user_id,
                display_name,
                created_at
            FROM app_users
            WHERE external_user_id = %s
        """

        with self._connection_factory() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(sql, (external_user_id,))
                return cursor.fetchone()
