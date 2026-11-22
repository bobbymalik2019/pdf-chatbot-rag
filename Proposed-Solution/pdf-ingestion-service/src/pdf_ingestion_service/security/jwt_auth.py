
import logging
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jwt.exceptions import PyJWTError
from redis.exceptions import RedisError

from pdf_ingestion_service.config.settings import settings
from pdf_ingestion_service.security.jwks_refresh_coordinator import (
    jwks_refresh_coordinator,
)


logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


class JWKSInfrastructureError(Exception):
    """Shared JWKS infrastructure is unavailable."""


def _retrieve_jwks(
    kid: str | None = None,
) -> dict:
    """
    Use the shared Redis-backed coordinator.

    With a kid, request a coordinated refresh when
    that key is absent from the cached JWKS.
    """
    try:
        if kid is None:
            return jwks_refresh_coordinator.get_jwks()

        return (
            jwks_refresh_coordinator
            .refresh_for_unknown_kid(kid)
        )

    except (
        RedisError,
        TimeoutError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        raise JWKSInfrastructureError(
            "Unable to retrieve Charter26 JWKS"
        ) from exc


def _find_signing_key(
    jwks: dict,
    kid: str,
):
    """
    Select an RSA signing key matching the JWT kid.

    This does not validate the JWT signature.
    Signature verification occurs in jwt.decode().
    """
    try:
        key_set = jwt.PyJWKSet.from_dict(jwks)
    except (PyJWTError, ValueError, TypeError) as exc:
        raise JWKSInfrastructureError(
            "Invalid JWKS received from shared cache"
        ) from exc

    for signing_key in key_set.keys:
        if (
            signing_key.key_id == kid
            and signing_key.key_type == "RSA"
            and signing_key.algorithm_name == "RS256"
            and signing_key.public_key_use in (None, "sig")
        ):
            return signing_key

    return None


def get_signing_key(token: str):
    """
    Resolve a JWT signing key using shared Redis JWKS.

    Unknown kid triggers at most one coordinated
    forced-refresh attempt per verification.
    """
    header = jwt.get_unverified_header(token)

    if header.get("alg") != "RS256":
        raise jwt.InvalidTokenError(
            "Unsupported JWT algorithm"
        )

    kid = header.get("kid")

    if (
        not isinstance(kid, str)
        or not kid
        or len(kid) > 128
    ):
        raise jwt.InvalidTokenError(
            "Invalid JWT key identifier"
        )

    jwks = _retrieve_jwks()

    signing_key = _find_signing_key(jwks, kid)

    if signing_key is not None:
        return signing_key

    # Charter26 may have rotated its signing key.
    # The coordinator enforces distributed locking
    # and a shared forced-refresh cooldown.
    refreshed_jwks = _retrieve_jwks(kid=kid)

    signing_key = _find_signing_key(
        refreshed_jwks,
        kid,
    )

    if signing_key is None:
        raise jwt.InvalidTokenError(
            "JWT signing key not found"
        )

    return signing_key


def verify_access_token(token: str) -> dict:
    try:
        signing_key = get_signing_key(token)

        claims = jwt.decode(
            token,
            key=signing_key.key,
            algorithms=["RS256"],
            issuer=settings.oidc_issuer.rstrip("/"),
            audience=settings.oidc_audience,
            leeway=15,
            options={
                "require": [
                    "iss",
                    "sub",
                    "aud",
                    "iat",
                    "nbf",
                    "exp",
                    "client_id",
                ]
            },
        )

        if (
            claims.get("client_id")
            != settings.oidc_client_id
        ):
            raise jwt.InvalidTokenError(
                "Unexpected OAuth client"
            )

        subject = claims.get("sub")

        if not isinstance(subject, str):
            raise jwt.InvalidTokenError(
                "Invalid subject"
            )

        UUID(subject)

        if "openid" not in str(
            claims.get("scope", "")
        ).split():
            raise jwt.InvalidTokenError(
                "Required scope missing"
            )

        return claims

    except JWKSInfrastructureError as exc:
        logger.warning(
            "Charter26 JWKS infrastructure unavailable"
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from exc

    except (PyJWTError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        ) from exc


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> dict:
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer access token required",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    return verify_access_token(
        credentials.credentials
    )
