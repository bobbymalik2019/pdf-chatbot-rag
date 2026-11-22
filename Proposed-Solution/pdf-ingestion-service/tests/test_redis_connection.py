
from pdf_ingestion_service.security.redis_client import (
    redis_connection_factory,
)


def test_redis_connection():
    assert redis_connection_factory.ping() is True
