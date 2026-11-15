
import psycopg
from psycopg import Connection


class DatabaseConnectionFactory:

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def get_connection(self) -> Connection:
        return psycopg.connect(self.connection_string)
