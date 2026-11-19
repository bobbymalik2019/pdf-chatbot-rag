import base64
import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from .settings import get_settings

_hasher = PasswordHasher()


def hash_password(value: str) -> str:
    if not value or len(value) > 1024:
        raise ValueError('Invalid password length')
    return _hasher.hash(value)


def verify_password(value: str, encoded: str) -> bool:
    try:
        return _hasher.verify(encoded, value)
    except (VerifyMismatchError, VerificationError, InvalidHashError, TypeError):
        return False


def digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def random_token(nbytes=32) -> str:
    return secrets.token_urlsafe(nbytes)


def pkce_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode('ascii')).digest()).rstrip(b'=').decode()


def safe_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def private_key():
    return Path(get_settings().signing_private_key_file).read_text(encoding='utf-8')


def public_key():
    return Path(get_settings().signing_public_key_file).read_text(encoding='utf-8')


def sign_claims(claims: dict) -> str:
    return jwt.encode(claims, private_key(), algorithm='RS256', headers={'kid': get_settings().signing_key_id, 'typ': 'JWT'})


def issue_tokens(user_id, client_id, audience, roles, nonce=None):
    cfg = get_settings()
    now = int(time.time())
    access = sign_claims({
        'iss': cfg.issuer, 'sub': str(user_id), 'aud': audience,
        'iat': now, 'nbf': now, 'exp': now + cfg.access_token_seconds,
        'jti': str(uuid4()), 'client_id': client_id,
        'scope': 'openid profile', 'roles': sorted(roles),
    })
    id_claims = {
        'iss': cfg.issuer, 'sub': str(user_id), 'aud': client_id,
        'iat': now, 'exp': now + cfg.access_token_seconds,
    }
    if nonce:
        id_claims['nonce'] = nonce
    return access, sign_claims(id_claims)


def jwks():
    key = serialization.load_pem_public_key(public_key().encode())
    numbers = key.public_numbers()

    def encode_int(num):
        return base64.urlsafe_b64encode(num.to_bytes((num.bit_length() + 7)//8, 'big')).rstrip(b'=').decode()

    return {'keys': [{'kty': 'RSA', 'use': 'sig', 'alg': 'RS256', 'kid': get_settings().signing_key_id, 'n': encode_int(numbers.n), 'e': encode_int(numbers.e)}]}
