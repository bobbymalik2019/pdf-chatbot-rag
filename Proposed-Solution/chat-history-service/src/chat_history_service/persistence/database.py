
import psycopg
from psycopg import Connection
from psycopg.conninfo import make_conninfo

from chat_history_service.config.settings import settings


class DatabaseConnectionFactory:

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def get_connection(self) -> Connection:
        return psycopg.connect(self.connection_string)


# Build the connection string safely from individual settings.
# make_conninfo handles passwords containing special characters.
connection_string = make_conninfo(
    host=settings.db_host,
    port=settings.db_port,
    dbname=settings.db_name,
    user=settings.db_user,
    password=settings.db_password,
    connect_timeout=5,
)

database_connection_factory = DatabaseConnectionFactory(
    connection_string=connection_string
)
