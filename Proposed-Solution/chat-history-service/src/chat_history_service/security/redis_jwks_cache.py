
import json
import logging

from redis import Redis

from chat_history_service.config.settings import settings
from chat_history_service.security.redis_client import (
    redis_connection_factory,
)


logger = logging.getLogger(__name__)


class RedisJWKSCache:
    """
    Shared Redis-backed storage for Charter26 public JWKS.

    This component does not fetch or validate JWTs.
    It only stores and retrieves public signing keys.
    """

    def __init__(
        self,
        redis_client: Redis,
        cache_key: str,
        ttl_seconds: int = 300,
    ):
        if not cache_key:
            raise ValueError("JWKS cache key is required")

        if ttl_seconds <= 0:
            raise ValueError("JWKS cache TTL must be positive")

        self._redis = redis_client
        self._cache_key = cache_key
        self._ttl_seconds = ttl_seconds

    @staticmethod
    def _validate_jwks(jwks: dict) -> None:
        if not isinstance(jwks, dict):
            raise ValueError("JWKS must be a dictionary")

        keys = jwks.get("keys")

        if not isinstance(keys, list) or not keys:
            raise ValueError(
                "JWKS must contain a non-empty keys list"
            )

        for key in keys:
            if not isinstance(key, dict):
                raise ValueError("Invalid JWKS key entry")

            if (
                key.get("kty") != "RSA"
                or not isinstance(key.get("kid"), str)
                or not key["kid"]
                or not isinstance(key.get("n"), str)
                or not key["n"]
                or not isinstance(key.get("e"), str)
                or not key["e"]
            ):
                raise ValueError(
                    "JWKS must contain RSA public signing keys"
                )

            private_fields = {
                "d", "p", "q", "dp",
                "dq", "qi", "oth", "k",
            }

            if private_fields.intersection(key):
                raise ValueError(
                    "Private key material must not be cached"
                )

    def get_jwks(self) -> dict | None:
        """
        Return cached JWKS or None on a cache miss.

        Redis connectivity failures and malformed cached
        data are not silently treated as cache misses.
        """

        cached_value = self._redis.get(self._cache_key)

        if cached_value is None:
            logger.debug("JWKS cache miss")
            return None

        try:
            jwks = json.loads(cached_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Invalid JSON in JWKS cache"
            ) from exc

        self._validate_jwks(jwks)

        logger.debug("JWKS cache hit")
        return jwks

    def set_jwks(self, jwks: dict) -> None:
        """
        Store a validated public JWKS with expiration.
        The caller must obtain JWKS from the trusted issuer.
        """

        self._validate_jwks(jwks)

        serialized = json.dumps(jwks)

        result = self._redis.setex(
            self._cache_key,
            self._ttl_seconds,
            serialized,
        )

        if not result:
            raise RuntimeError("Unable to store JWKS in Redis")

        logger.info(
            "JWKS cached successfully | ttl=%d seconds",
            self._ttl_seconds,
        )


redis_jwks_cache = RedisJWKSCache(
    redis_client=redis_connection_factory.get_client(),
    cache_key=settings.jwks_cache_key,
    ttl_seconds=settings.jwks_cache_ttl_seconds,
)

