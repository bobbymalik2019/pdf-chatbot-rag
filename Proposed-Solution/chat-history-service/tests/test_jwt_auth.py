
import time
from uuid import uuid4

import jwt
import pytest

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jwt.algorithms import RSAAlgorithm
from redis.exceptions import RedisError

from chat_history_service.security import jwt_auth


@pytest.fixture
def signing_key():
    """Generate a real RSA key pair for JWT signing."""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


def make_jwks(private_key, kid="test-key-1"):
    """Create a public-only JWKS."""
    jwk = RSAAlgorithm.to_jwk(
        private_key.public_key(),
        as_dict=True,
    )
    jwk.update({
        "kid": kid,
        "alg": "RS256",
        "use": "sig",
    })
    return {"keys": [jwk]}


def make_token(private_key, kid="test-key-1", **overrides):
    now = int(time.time())

    claims = {
        "iss": jwt_auth.settings.oidc_issuer.rstrip("/"),
        "sub": str(uuid4()),
        "aud": jwt_auth.settings.oidc_audience,
        "iat": now,
        "nbf": now,
        "exp": now + 3600,
        "client_id": jwt_auth.settings.oidc_client_id,
        "scope": "openid profile",
    }

    claims.update(overrides)

    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )


def mock_jwks(monkeypatch, jwks):
    """Replace the Redis coordinator with local test data."""
    monkeypatch.setattr(
        jwt_auth.jwks_refresh_coordinator,
        "get_jwks",
        lambda: jwks,
    )


def assert_http_status(expected_status, operation):
    with pytest.raises(HTTPException) as exc:
        operation()

    assert exc.value.status_code == expected_status


def test_valid_signed_token(monkeypatch, signing_key):
    mock_jwks(monkeypatch, make_jwks(signing_key))

    token = make_token(signing_key)
    claims = jwt_auth.verify_access_token(token)

    assert claims["aud"] == jwt_auth.settings.oidc_audience
    assert claims["client_id"] == jwt_auth.settings.oidc_client_id
    assert "openid" in claims["scope"].split()


def test_invalid_signature(monkeypatch, signing_key):
    mock_jwks(monkeypatch, make_jwks(signing_key))

    attacker_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    token = make_token(attacker_key)

    assert_http_status(
        401,
        lambda: jwt_auth.verify_access_token(token),
    )


def test_expired_token(monkeypatch, signing_key):
    mock_jwks(monkeypatch, make_jwks(signing_key))

    token = make_token(
        signing_key,
        exp=int(time.time()) - 120,
    )

    assert_http_status(
        401,
        lambda: jwt_auth.verify_access_token(token),
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "some-other-service"},
        {"iss": "https://untrusted.example.com"},
        {"client_id": "unknown-client"},
        {"scope": "profile email"},
        {"sub": "not-a-uuid"},
    ],
)
def test_invalid_claims(
    monkeypatch,
    signing_key,
    overrides,
):
    mock_jwks(monkeypatch, make_jwks(signing_key))

    token = make_token(signing_key, **overrides)

    assert_http_status(
        401,
        lambda: jwt_auth.verify_access_token(token),
    )


def test_unknown_kid(monkeypatch, signing_key):
    jwks = make_jwks(signing_key, kid="known-key")

    mock_jwks(monkeypatch, jwks)

    calls = []

    def fake_refresh(kid):
        calls.append(kid)
        return jwks

    monkeypatch.setattr(
        jwt_auth.jwks_refresh_coordinator,
        "refresh_for_unknown_kid",
        fake_refresh,
    )

    token = make_token(signing_key, kid="unknown-key")

    assert_http_status(
        401,
        lambda: jwt_auth.verify_access_token(token),
    )

    assert calls == ["unknown-key"]


def test_signing_key_rotation(monkeypatch, signing_key):
    old_jwks = make_jwks(signing_key, kid="old-key")

    rotated_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    new_jwks = make_jwks(rotated_key, kid="new-key")

    mock_jwks(monkeypatch, old_jwks)

    calls = []

    def fake_refresh(kid):
        calls.append(kid)
        return new_jwks

    monkeypatch.setattr(
        jwt_auth.jwks_refresh_coordinator,
        "refresh_for_unknown_kid",
        fake_refresh,
    )

    token = make_token(rotated_key, kid="new-key")

    claims = jwt_auth.verify_access_token(token)

    assert claims["client_id"] == jwt_auth.settings.oidc_client_id
    assert calls == ["new-key"]


def test_redis_failure_returns_503(monkeypatch, signing_key):
    def failing_jwks():
        raise RedisError("Redis unavailable")

    monkeypatch.setattr(
        jwt_auth.jwks_refresh_coordinator,
        "get_jwks",
        failing_jwks,
    )

    token = make_token(signing_key)

    assert_http_status(
        503,
        lambda: jwt_auth.verify_access_token(token),
    )


def test_missing_bearer_token():
    assert_http_status(
        401,
        lambda: jwt_auth.get_current_principal(None),
    )
