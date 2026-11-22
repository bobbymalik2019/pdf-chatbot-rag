
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from pdf_ingestion_service.security.redis_client import (
    redis_connection_factory,
)
from pdf_ingestion_service.security.redis_jwks_cache import (
    RedisJWKSCache,
)
from pdf_ingestion_service.security.jwks_refresh_coordinator import (
    JWKSRefreshCoordinator,
)


def make_jwks(kid: str) -> dict:
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": kid,
                "use": "sig",
                "alg": "RS256",
                "n": "test-modulus",
                "e": "AQAB",
            }
        ]
    }


@pytest.fixture
def redis_environment():
    client = redis_connection_factory.get_client()

    assert client.ping()

    # Never use the application's real JWKS cache key.
    cache_key = f"test:charter26:jwks:{uuid4().hex}"

    try:
        yield client, cache_key
    finally:
        client.delete(
            cache_key,
            f"{cache_key}:refresh-lock",
            f"{cache_key}:forced-refresh-cooldown",
        )


def make_coordinator(
    client,
    cache_key,
    fetcher,
    lock_seconds=5,
):
    cache = RedisJWKSCache(
        redis_client=client,
        cache_key=cache_key,
        ttl_seconds=300,
    )

    return JWKSRefreshCoordinator(
        cache=cache,
        redis_client=client,
        fetch_jwks=fetcher,
        cache_key=cache_key,
        ttl_seconds=300,
        lock_seconds=lock_seconds,
        wait_seconds=4,
        poll_seconds=0.02,
        forced_refresh_cooldown_seconds=30,
    )


def test_concurrent_cache_miss_fetches_once(
    redis_environment,
):
    client, cache_key = redis_environment

    fetch_started = threading.Event()
    release_fetch = threading.Event()
    fetch_count = 0
    count_lock = threading.Lock()

    jwks = make_jwks("key-1")

    def fetcher():
        nonlocal fetch_count

        with count_lock:
            fetch_count += 1

        fetch_started.set()

        if not release_fetch.wait(timeout=3):
            raise TimeoutError("Test fetch was not released")

        return jwks

    # Two independent coordinators, same Redis namespace.
    rag = make_coordinator(client, cache_key, fetcher)
    history = make_coordinator(client, cache_key, fetcher)

    with ThreadPoolExecutor(max_workers=2) as pool:
        try:
            first = pool.submit(rag.get_jwks)

            assert fetch_started.wait(timeout=2)

            second = pool.submit(history.get_jwks)

            # Give the second caller an opportunity to
            # encounter the existing Redis lock.
            time.sleep(0.1)

            assert not second.done()

        finally:
            release_fetch.set()

        result1 = first.result(timeout=4)
        result2 = second.result(timeout=4)

    assert result1 == jwks
    assert result2 == jwks
    assert fetch_count == 1

    assert client.get(cache_key) is not None
    assert client.ttl(cache_key) > 0


def test_forced_refresh_preserves_cached_reads(
    redis_environment,
):
    client, cache_key = redis_environment

    old_jwks = make_jwks("old-key")
    new_jwks = make_jwks("new-key")

    cache = RedisJWKSCache(
        redis_client=client,
        cache_key=cache_key,
        ttl_seconds=300,
    )

    cache.set_jwks(old_jwks)

    fetch_started = threading.Event()
    release_fetch = threading.Event()

    def fetcher():
        fetch_started.set()

        if not release_fetch.wait(timeout=3):
            raise TimeoutError("Test fetch was not released")

        return new_jwks

    rag = make_coordinator(client, cache_key, fetcher)
    history = make_coordinator(client, cache_key, fetcher)

    with ThreadPoolExecutor(max_workers=2) as pool:
        try:
            refresh = pool.submit(
                rag.refresh_for_unknown_kid,
                "new-key",
            )

            assert fetch_started.wait(timeout=2)

            # An ordinary request can continue using
            # the currently cached JWKS during refresh.
            current = history.get_jwks()

            assert current == old_jwks

        finally:
            release_fetch.set()

        refreshed = refresh.result(timeout=4)

    assert refreshed == new_jwks
    assert history.get_jwks() == new_jwks
    assert client.exists(
        f"{cache_key}:forced-refresh-cooldown"
    ) == 1


def test_expired_lock_cannot_overwrite_newer_jwks(
    redis_environment,
):
    client, cache_key = redis_environment

    first_started = threading.Event()
    release_first = threading.Event()

    old_jwks = make_jwks("old-key")
    new_jwks = make_jwks("new-key")

    def slow_fetcher():
        first_started.set()

        if not release_first.wait(timeout=3):
            raise TimeoutError("Slow fetch was not released")

        return old_jwks

    def new_fetcher():
        return new_jwks

    first_coordinator = make_coordinator(
        client,
        cache_key,
        slow_fetcher,
        lock_seconds=1,
    )

    second_coordinator = make_coordinator(
        client,
        cache_key,
        new_fetcher,
        lock_seconds=5,
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        try:
            first = pool.submit(first_coordinator.get_jwks)

            assert first_started.wait(timeout=2)

            # Let the first worker's Redis lock expire.
            time.sleep(1.15)

            second = pool.submit(second_coordinator.get_jwks)

            assert second.result(timeout=3) == new_jwks

        finally:
            release_first.set()

        with pytest.raises(
            RuntimeError,
            match="lock expired",
        ):
            first.result(timeout=4)

    # The stale worker must not overwrite the newer keys.
    assert (
        second_coordinator.get_jwks()
        == new_jwks
    )


def test_normal_refresh_overlaps_forced_refresh(
    redis_environment,
):
    """
    A normal cache miss obtains the refresh lock.
    A concurrent unknown-kid request must reuse
    the resulting JWKS rather than fetch it again.
    """
    client, cache_key = redis_environment

    fetch_started = threading.Event()
    release_fetch = threading.Event()
    count_lock = threading.Lock()
    fetch_count = 0

    new_jwks = make_jwks("rotated-key")

    def fetcher():
        nonlocal fetch_count

        with count_lock:
            fetch_count += 1

        fetch_started.set()

        if not release_fetch.wait(timeout=3):
            raise TimeoutError(
                "Test fetch was not released"
            )

        return new_jwks

    rag = make_coordinator(
        client, cache_key, fetcher
    )

    history = make_coordinator(
        client, cache_key, fetcher
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        try:
            normal_request = pool.submit(
                rag.get_jwks
            )

            assert fetch_started.wait(timeout=2)

            forced_request = pool.submit(
                history.refresh_for_unknown_kid,
                "rotated-key",
            )

            time.sleep(0.1)

            assert not forced_request.done()

        finally:
            release_fetch.set()

        normal_result = normal_request.result(
            timeout=4
        )

        forced_result = forced_request.result(
            timeout=4
        )

    assert normal_result == new_jwks
    assert forced_result == new_jwks
    assert fetch_count == 1
