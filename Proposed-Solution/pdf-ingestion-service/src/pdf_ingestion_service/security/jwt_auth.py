import logging
import ssl
from functools import lru_cache
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import (
    PyJWTError,
    PyJWKClientConnectionError,
)

from pdf_ingestion_service.config.settings import settings

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def get_jwks_client() -> PyJWKClient:
    issuer = settings.oidc_issuer.rstrip("/")

    if not issuer.startswith("https://"):
        raise RuntimeError("OIDC issuer must use HTTPS")

    ssl_context = (
        ssl.create_default_context(
            cafile=str(settings.oidc_ca_cert_file)
        )
        if settings.oidc_ca_cert_file
        else ssl.create_default_context()
    )

    return PyJWKClient(
        uri=f"{issuer}/.well-known/jwks.json",
        cache_jwk_set=True,
        lifespan=300,
        timeout=5,
        ssl_context=ssl_context,
    )


def verify_access_token(token: str) -> dict:
    try:
        signing_key = get_jwks_client().get_signing_key_from_jwt(
            token
        )

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

        if claims.get("client_id") != settings.oidc_client_id:
            raise jwt.InvalidTokenError("Unexpected OAuth client")

        subject = claims.get("sub")

        if not isinstance(subject, str):
            raise jwt.InvalidTokenError("Invalid subject")

        UUID(subject)

        if "openid" not in str(
            claims.get("scope", "")
        ).split():
            raise jwt.InvalidTokenError("Required scope missing")

        return claims

    except PyJWKClientConnectionError as exc:
        logger.warning("Charter26 JWKS endpoint unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from exc

    except (PyJWTError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
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
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verify_access_token(credentials.credentials)
