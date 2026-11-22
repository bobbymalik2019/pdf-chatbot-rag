
import json
import logging
import ssl
import time

from collections.abc import Callable
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4

from redis import Redis

from pdf_ingestion_service.config.settings import settings
from pdf_ingestion_service.security.redis_client import (
    redis_connection_factory,
)
from pdf_ingestion_service.security.redis_jwks_cache import (
    RedisJWKSCache,
    redis_jwks_cache,
)


logger = logging.getLogger(__name__)


_RELEASE_LOCK_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
end
return 0
"""


_PUBLISH_JWKS_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    redis.call("SETEX", KEYS[2], ARGV[2], ARGV[3])
    redis.call("DEL", KEYS[1])
    return 1
end
return 0
"""


# Atomically publish new JWKS and start the forced-refresh
# cooldown, but only if the caller still owns the lock.
_PUBLISH_FORCED_REFRESH_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    redis.call("SETEX", KEYS[2], ARGV[2], ARGV[3])
    redis.call("SETEX", KEYS[3], ARGV[4], "1")
    redis.call("DEL", KEYS[1])
    return 1
end
return 0
"""


def fetch_charter26_jwks(
    issuer: str,
    ca_cert_file: Path | None = None,
) -> dict:
    issuer = issuer.rstrip("/")

    if not issuer.startswith("https://"):
        raise ValueError("OIDC issuer must use HTTPS")

    context = (
        ssl.create_default_context(cafile=str(ca_cert_file))
        if ca_cert_file
        else ssl.create_default_context()
    )

    url = f"{issuer}/.well-known/jwks.json"

    request = Request(
        url,
        headers={"Accept": "application/json"},
    )

    with urlopen(
        request,
        timeout=5,
        context=context,
    ) as response:
        if response.status != 200:
            raise RuntimeError(
                "JWKS endpoint returned an unexpected status"
            )

        payload = response.read(1_048_577)

        if len(payload) > 1_048_576:
            raise ValueError("JWKS response is too large")

        return json.loads(payload)


class JWKSRefreshCoordinator:

    def __init__(
        self,
        cache: RedisJWKSCache,
        redis_client: Redis,
        fetch_jwks: Callable[[], dict],
        cache_key: str,
        ttl_seconds: int = 300,
        lock_seconds: int = 15,
        wait_seconds: float = 8,
        poll_seconds: float = 0.1,
        forced_refresh_cooldown_seconds: int = 30,
    ):
        if not cache_key:
            raise ValueError("Cache key is required")

        if ttl_seconds <= 0 or lock_seconds <= 0:
            raise ValueError(
                "TTL and lock lifetime must be positive"
            )

        if wait_seconds <= 0 or poll_seconds <= 0:
            raise ValueError(
                "Wait and poll intervals must be positive"
            )

        if forced_refresh_cooldown_seconds <= 0:
            raise ValueError(
                "Forced refresh cooldown must be positive"
            )

        self._cache = cache
        self._redis = redis_client
        self._fetch_jwks = fetch_jwks
        self._cache_key = cache_key

        self._lock_key = f"{cache_key}:refresh-lock"
        self._cooldown_key = f"{cache_key}:forced-refresh-cooldown"

        self._ttl_seconds = ttl_seconds
        self._lock_seconds = lock_seconds
        self._wait_seconds = wait_seconds
        self._poll_seconds = poll_seconds
        self._forced_refresh_cooldown_seconds = (
            forced_refresh_cooldown_seconds
        )

    @staticmethod
    def _contains_kid(jwks: dict | None, kid: str) -> bool:
        if jwks is None:
            return False

        return any(
            isinstance(key, dict)
            and key.get("kid") == kid
            for key in jwks.get("keys", [])
        )

    def _release_lock(self, token: str) -> None:
        self._redis.eval(
            _RELEASE_LOCK_SCRIPT,
            1,
            self._lock_key,
            token,
        )

    def get_jwks(self) -> dict:
        """
        Normal cache-first JWKS retrieval.
        Existing behavior is preserved.
        """
        cached = self._cache.get_jwks()

        if cached is not None:
            return cached

        deadline = time.monotonic() + self._wait_seconds

        while time.monotonic() < deadline:
            lock_token = str(uuid4())

            acquired = self._redis.set(
                self._lock_key,
                lock_token,
                nx=True,
                ex=self._lock_seconds,
            )

            if acquired:
                return self._refresh_under_lock(lock_token)

            cached = self._cache.get_jwks()

            if cached is not None:
                return cached

            time.sleep(
                min(
                    self._poll_seconds,
                    max(0, deadline - time.monotonic()),
                )
            )

        raise TimeoutError(
            "Timed out waiting for shared JWKS refresh"
        )

    def _refresh_under_lock(
        self,
        lock_token: str,
    ) -> dict:
        try:
            cached = self._cache.get_jwks()

            if cached is not None:
                return cached

            logger.info("Refreshing Charter26 JWKS")

            jwks = self._fetch_jwks()
            self._cache._validate_jwks(jwks)

            published = self._redis.eval(
                _PUBLISH_JWKS_SCRIPT,
                2,
                self._lock_key,
                self._cache_key,
                lock_token,
                self._ttl_seconds,
                json.dumps(jwks),
            )

            if published != 1:
                raise RuntimeError(
                    "JWKS refresh lock expired before publication"
                )

            logger.info("Charter26 JWKS refresh completed")
            return jwks

        finally:
            self._release_lock(lock_token)

    def refresh_for_unknown_kid(self, kid: str) -> dict:
        """
        Coordinate a forced refresh when a JWT references
        a kid absent from the currently cached JWKS.

        The global cooldown prevents repeated refresh
        requests for arbitrary unknown key IDs.

        This method returns a JWKS; it does not assert that
        the requested kid exists. The JWT verifier must
        reject the token if the kid remains unknown.
        """
        if (
            not isinstance(kid, str)
            or not kid
            or len(kid) > 128
        ):
            raise ValueError("Invalid JWT key identifier")

        # Ensure normal cache-miss handling runs first.
        current = self.get_jwks()

        if self._contains_kid(current, kid):
            return current

        deadline = time.monotonic() + self._wait_seconds

        while time.monotonic() < deadline:
            # Another service may have refreshed the JWKS.
            current = self._cache.get_jwks()

            if self._contains_kid(current, kid):
                return current

            # An earlier forced refresh limits subsequent
            # refreshes, even for different unknown kids.
            if self._redis.exists(self._cooldown_key):
                    if current is None:
                        raise RuntimeError(
                            "JWKS unavailable during forced-refresh cooldown"
                        )
                    return current

            lock_token = str(uuid4())

            acquired = self._redis.set(
                self._lock_key,
                lock_token,
                nx=True,
                ex=self._lock_seconds,
            )

            if acquired:
                return self._force_refresh_under_lock(
                    lock_token,
                    kid,
                )

            time.sleep(
                min(
                    self._poll_seconds,
                    max(0, deadline - time.monotonic()),
                )
            )

        raise TimeoutError(
            "Timed out waiting for coordinated JWKS refresh"
        )

    def _force_refresh_under_lock(
        self,
        lock_token: str,
        kid: str,
    ) -> dict:
        try:
            # Recheck after lock acquisition.
            current = self._cache.get_jwks()

            if self._contains_kid(current, kid):
                return current

            if self._redis.exists(self._cooldown_key):
                if current is None:
                    raise RuntimeError(
                                        "JWKS unavailable during forced-refresh cooldown"
                )
                return current

            logger.info(
                "Performing coordinated JWKS forced refresh"
            )

            refreshed = self._fetch_jwks()
            self._cache._validate_jwks(refreshed)

            published = self._redis.eval(
                _PUBLISH_FORCED_REFRESH_SCRIPT,
                3,
                self._lock_key,
                self._cache_key,
                self._cooldown_key,
                lock_token,
                self._ttl_seconds,
                json.dumps(refreshed),
                self._forced_refresh_cooldown_seconds,
            )

            if published != 1:
                raise RuntimeError(
                    "JWKS refresh lock expired before publication"
                )

            logger.info(
                "Coordinated JWKS forced refresh completed"
            )

            return refreshed

        finally:
            self._release_lock(lock_token)


def _fetch_configured_jwks() -> dict:
    return fetch_charter26_jwks(
        issuer=settings.oidc_issuer,
        ca_cert_file=settings.oidc_ca_cert_file,
    )


jwks_refresh_coordinator = JWKSRefreshCoordinator(
    cache=redis_jwks_cache,
    redis_client=redis_connection_factory.get_client(),
    fetch_jwks=_fetch_configured_jwks,
    cache_key=settings.jwks_cache_key,
    ttl_seconds=settings.jwks_cache_ttl_seconds,
    lock_seconds=settings.jwks_refresh_lock_seconds,
    forced_refresh_cooldown_seconds=(
        settings.jwks_forced_refresh_cooldown_seconds
    ),
)
