
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from redis.exceptions import ConnectionError as RedisConnectionError

from pdf_ingestion_service.security import jwt_auth


@pytest.fixture
def signing_material():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    public_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(
        private_key.public_key(),
        as_dict=True,
    )

    public_jwk.update({
        "kid": "test-key-v1",
        "alg": "RS256",
        "use": "sig",
    })

    return private_key, {"keys": [public_jwk]}


@pytest.fixture
def token_factory(signing_material):
    private_key, _ = signing_material

    def create_token(
        key=None,
        kid="test-key-v1",
        expires_in_seconds=300,
        scope="openid profile",
        client_id=None,
    ):
        now = datetime.now(timezone.utc)

        claims = {
            "iss": jwt_auth.settings.oidc_issuer.rstrip("/"),
            "sub": str(uuid4()),
            "aud": jwt_auth.settings.oidc_audience,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(
                seconds=expires_in_seconds
            ),
            "client_id": (
                client_id
                if client_id is not None
                else jwt_auth.settings.oidc_client_id
            ),
            "scope": scope,
        }

        return jwt.encode(
            claims,
            key or private_key,
            algorithm="RS256",
            headers={"kid": kid},
        )

    return create_token


@pytest.fixture
def coordinator_mock(monkeypatch, signing_material):
    _, jwks = signing_material

    coordinator = Mock()
    coordinator.get_jwks.return_value = jwks
    coordinator.refresh_for_unknown_kid.return_value = jwks

    monkeypatch.setattr(
        jwt_auth,
        "jwks_refresh_coordinator",
        coordinator,
    )

    return coordinator


def test_valid_rs256_token(
    token_factory,
    coordinator_mock,
):
    token = token_factory()

    claims = jwt_auth.verify_access_token(token)

    assert "openid" in claims["scope"]
    assert claims["client_id"] == (
        jwt_auth.settings.oidc_client_id
    )

    coordinator_mock.get_jwks.assert_called_once()
    coordinator_mock.refresh_for_unknown_kid.assert_not_called()


def test_invalid_signature_rejected(
    token_factory,
    coordinator_mock,
):
    wrong_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    token = token_factory(key=wrong_key)

    with pytest.raises(HTTPException) as exc:
        jwt_auth.verify_access_token(token)

    assert exc.value.status_code == 401


def test_expired_token_rejected(
    token_factory,
    coordinator_mock,
):
    # Beyond the existing 15-second JWT leeway.
    token = token_factory(expires_in_seconds=-120)

    with pytest.raises(HTTPException) as exc:
        jwt_auth.verify_access_token(token)

    assert exc.value.status_code == 401


def test_missing_openid_scope_rejected(
    token_factory,
    coordinator_mock,
):
    token = token_factory(scope="profile")

    with pytest.raises(HTTPException) as exc:
        jwt_auth.verify_access_token(token)

    assert exc.value.status_code == 401


def test_wrong_client_id_rejected(
    token_factory,
    coordinator_mock,
):
    token = token_factory(
        client_id="unauthorized-client"
    )

    with pytest.raises(HTTPException) as exc:
        jwt_auth.verify_access_token(token)

    assert exc.value.status_code == 401


def test_unknown_kid_rejected(
    token_factory,
    coordinator_mock,
):
    token = token_factory(kid="unknown-key")

    with pytest.raises(HTTPException) as exc:
        jwt_auth.verify_access_token(token)

    assert exc.value.status_code == 401

    coordinator_mock.refresh_for_unknown_kid.assert_called_once_with(
        "unknown-key"
    )


def test_key_rotation(
    signing_material,
    token_factory,
    coordinator_mock,
):
    _, old_jwks = signing_material

    new_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    new_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(
        new_private_key.public_key(),
        as_dict=True,
    )

    new_jwk.update({
        "kid": "test-key-v2",
        "alg": "RS256",
        "use": "sig",
    })

    coordinator_mock.refresh_for_unknown_kid.return_value = {
        "keys": [
            *old_jwks["keys"],
            new_jwk,
        ]
    }

    token = token_factory(
        key=new_private_key,
        kid="test-key-v2",
    )

    claims = jwt_auth.verify_access_token(token)

    assert "openid" in claims["scope"]

    coordinator_mock.refresh_for_unknown_kid.assert_called_once_with(
        "test-key-v2"
    )


def test_redis_failure_returns_503(
    token_factory,
    coordinator_mock,
):
    coordinator_mock.get_jwks.side_effect = (
        RedisConnectionError("Redis unavailable")
    )

    with pytest.raises(HTTPException) as exc:
        jwt_auth.verify_access_token(
            token_factory()
        )

    assert exc.value.status_code == 503


def test_refresh_failure_returns_503(
    token_factory,
    coordinator_mock,
):
    coordinator_mock.refresh_for_unknown_kid.side_effect = (
        TimeoutError("Refresh timed out")
    )

    with pytest.raises(HTTPException) as exc:
        jwt_auth.verify_access_token(
            token_factory(kid="new-key")
        )

    assert exc.value.status_code == 503
