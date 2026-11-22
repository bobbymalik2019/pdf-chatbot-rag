
import redis

from pdf_ingestion_service.config.settings import settings


class RedisConnectionFactory:

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
    ):
        self._client = redis.Redis(
            host=host,
            port=port,
            username=username,
            password=password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

    def get_client(self) -> redis.Redis:
        return self._client

    def ping(self) -> bool:
        return bool(self._client.ping())


redis_connection_factory = RedisConnectionFactory(
    host=settings.redis_host,
    port=settings.redis_port,
    username=settings.redis_username,
    password=settings.redis_password,
)
