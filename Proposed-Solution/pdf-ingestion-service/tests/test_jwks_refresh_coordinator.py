
from unittest.mock import Mock

import pytest

from pdf_ingestion_service.security.jwks_refresh_coordinator import (
    JWKSRefreshCoordinator,
)


@pytest.fixture
def sample_jwks():
    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "key-1",
                "n": "test-modulus",
                "e": "AQAB",
                "alg": "RS256",
            }
        ]
    }


@pytest.fixture
def redis_client():
    return Mock()


@pytest.fixture
def cache():
    mock_cache = Mock()
    mock_cache._validate_jwks = Mock()
    return mock_cache


@pytest.fixture
def fetcher(sample_jwks):
    return Mock(return_value=sample_jwks)


@pytest.fixture
def coordinator(cache, redis_client, fetcher):
    return JWKSRefreshCoordinator(
        cache=cache,
        redis_client=redis_client,
        fetch_jwks=fetcher,
        cache_key="test:charter26:jwks",
        wait_seconds=0.2,
        poll_seconds=0.01,
    )


def test_cache_hit_skips_refresh(
    coordinator,
    cache,
    redis_client,
    fetcher,
    sample_jwks,
):
    cache.get_jwks.return_value = sample_jwks

    assert coordinator.get_jwks() == sample_jwks

    redis_client.set.assert_not_called()
    fetcher.assert_not_called()


def test_cache_miss_refreshes_jwks(
    coordinator,
    cache,
    redis_client,
    fetcher,
    sample_jwks,
):
    cache.get_jwks.return_value = None
    redis_client.set.return_value = True
    redis_client.eval.return_value = 1

    result = coordinator.get_jwks()

    assert result == sample_jwks
    fetcher.assert_called_once()
    cache._validate_jwks.assert_called_once_with(
        sample_jwks
    )

    redis_client.set.assert_called_once()
    assert redis_client.eval.call_count == 2


def test_another_instance_refreshed_cache(
    coordinator,
    cache,
    redis_client,
    fetcher,
    sample_jwks,
):
    cache.get_jwks.side_effect = [
        None,
        sample_jwks,
    ]

    redis_client.set.return_value = None

    result = coordinator.get_jwks()

    assert result == sample_jwks
    fetcher.assert_not_called()


def test_second_cache_check_avoids_fetch(
    coordinator,
    cache,
    redis_client,
    fetcher,
    sample_jwks,
):
    cache.get_jwks.side_effect = [
        None,
        sample_jwks,
    ]

    redis_client.set.return_value = True

    result = coordinator.get_jwks()

    assert result == sample_jwks
    fetcher.assert_not_called()
    redis_client.eval.assert_called_once()


def test_refresh_failure_releases_lock(
    coordinator,
    cache,
    redis_client,
    fetcher,
):
    cache.get_jwks.return_value = None
    redis_client.set.return_value = True

    fetcher.side_effect = RuntimeError(
        "Charter26 unavailable"
    )

    with pytest.raises(
        RuntimeError,
        match="Charter26 unavailable",
    ):
        coordinator.get_jwks()

    # The finally block attempts ownership-safe release.
    redis_client.eval.assert_called_once()


def test_expired_lock_cannot_publish(
    coordinator,
    cache,
    redis_client,
):
    cache.get_jwks.return_value = None
    redis_client.set.return_value = True

    # Publication fails because lock ownership was lost.
    redis_client.eval.side_effect = [0, 0]

    with pytest.raises(
        RuntimeError,
        match="lock expired",
    ):
        coordinator.get_jwks()


def test_timeout_when_lock_unavailable(
    coordinator,
    cache,
    redis_client,
    fetcher,
):
    cache.get_jwks.return_value = None
    redis_client.set.return_value = None

    with pytest.raises(TimeoutError):
        coordinator.get_jwks()

    fetcher.assert_not_called()


def test_invalid_lock_configuration(
    cache,
    redis_client,
    fetcher,
):
    with pytest.raises(ValueError):
        JWKSRefreshCoordinator(
            cache=cache,
            redis_client=redis_client,
            fetch_jwks=fetcher,
            cache_key="test",
            lock_seconds=0,
        )


def test_unknown_kid_triggers_forced_refresh(
    coordinator,
    cache,
    redis_client,
    fetcher,
    sample_jwks,
):
    old_jwks = {
        "keys": [{"kid": "old-key"}]
    }

    cache.get_jwks.return_value = old_jwks
    redis_client.exists.return_value = 0
    redis_client.set.return_value = True
    redis_client.eval.return_value = 1

    result = coordinator.refresh_for_unknown_kid(
        "key-1"
    )

    assert result == sample_jwks
    fetcher.assert_called_once()


def test_known_kid_does_not_refresh(
    coordinator,
    cache,
    redis_client,
    fetcher,
    sample_jwks,
):
    cache.get_jwks.return_value = sample_jwks

    result = coordinator.refresh_for_unknown_kid(
        "key-1"
    )

    assert result == sample_jwks
    fetcher.assert_not_called()
    redis_client.set.assert_not_called()


def test_forced_refresh_respects_cooldown(
    coordinator,
    cache,
    redis_client,
    fetcher,
):
    cached_jwks = {
        "keys": [{"kid": "existing-key"}]
    }

    cache.get_jwks.return_value = cached_jwks
    redis_client.exists.return_value = 1

    result = coordinator.refresh_for_unknown_kid(
        "unknown-key"
    )

    assert result == cached_jwks
    fetcher.assert_not_called()


def test_forced_refresh_rejects_invalid_kid(
    coordinator,
):
    with pytest.raises(ValueError):
        coordinator.refresh_for_unknown_kid("")

    with pytest.raises(ValueError):
        coordinator.refresh_for_unknown_kid(
            "x" * 129
        )


def test_forced_refresh_lock_loss(
    coordinator,
    cache,
    redis_client,
):
    cache.get_jwks.return_value = {
        "keys": [{"kid": "old-key"}]
    }

    redis_client.exists.return_value = 0
    redis_client.set.return_value = True
    redis_client.eval.side_effect = [0, 0]

    with pytest.raises(
        RuntimeError,
        match="lock expired",
    ):
        coordinator.refresh_for_unknown_kid(
            "new-key"
        )


def test_forced_refresh_failure_releases_lock(
    coordinator,
    cache,
    redis_client,
    fetcher,
):
    cache.get_jwks.return_value = {
        "keys": [{"kid": "old-key"}]
    }

    redis_client.exists.return_value = 0
    redis_client.set.return_value = True

    fetcher.side_effect = RuntimeError(
        "Charter26 unavailable"
    )

    with pytest.raises(
        RuntimeError,
        match="Charter26 unavailable",
    ):
        coordinator.refresh_for_unknown_kid(
            "new-key"
        )

    redis_client.eval.assert_called_once()

