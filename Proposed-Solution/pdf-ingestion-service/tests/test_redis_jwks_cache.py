
import json
from unittest.mock import Mock

import pytest
from redis.exceptions import ConnectionError

from pdf_ingestion_service.security.redis_jwks_cache import (
    RedisJWKSCache,
)


@pytest.fixture
def sample_jwks():
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-key-1",
                "use": "sig",
                "alg": "RS256",
                "n": "test-modulus",
                "e": "AQAB",
            }
        ]
    }


@pytest.fixture
def redis_client():
    return Mock()


@pytest.fixture
def cache(redis_client):
    return RedisJWKSCache(
        redis_client=redis_client,
        cache_key="test:charter26:jwks",
        ttl_seconds=300,
    )


def test_cache_miss(cache, redis_client):
    redis_client.get.return_value = None

    assert cache.get_jwks() is None

    redis_client.get.assert_called_once_with(
        "test:charter26:jwks"
    )


def test_cache_hit(
    cache,
    redis_client,
    sample_jwks,
):
    redis_client.get.return_value = json.dumps(
        sample_jwks
    )

    result = cache.get_jwks()

    assert result == sample_jwks


def test_store_jwks(
    cache,
    redis_client,
    sample_jwks,
):
    redis_client.setex.return_value = True

    cache.set_jwks(sample_jwks)

    redis_client.setex.assert_called_once_with(
        "test:charter26:jwks",
        300,
        json.dumps(sample_jwks),
    )


def test_reject_invalid_jwks(cache):
    with pytest.raises(ValueError):
        cache.set_jwks({"invalid": "data"})


def test_reject_private_key_material(
    cache,
    sample_jwks,
):
    sample_jwks["keys"][0]["d"] = "private-exponent"

    with pytest.raises(ValueError):
        cache.set_jwks(sample_jwks)


def test_reject_corrupted_cache(
    cache,
    redis_client,
):
    redis_client.get.return_value = "not-json"

    with pytest.raises(ValueError):
        cache.get_jwks()


def test_redis_unavailable(
    cache,
    redis_client,
):
    redis_client.get.side_effect = ConnectionError(
        "Redis unavailable"
    )

    with pytest.raises(ConnectionError):
        cache.get_jwks()


def test_invalid_ttl(redis_client):
    with pytest.raises(ValueError):
        RedisJWKSCache(
            redis_client=redis_client,
            cache_key="test",
            ttl_seconds=0,
        )
