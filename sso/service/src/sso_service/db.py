from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row
from .settings import get_settings


@contextmanager
def connection():
    with psycopg.connect(get_settings().database_url, row_factory=dict_row) as conn:
        yield conn
