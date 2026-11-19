import base64
import re
from datetime import timedelta
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import APIRouter, Form, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from .auth import now_utc, find_session
from .db import connection
from .security import digest, random_token, pkce_challenge, safe_equals, issue_tokens, jwks
from .settings import get_settings

router = APIRouter()
PKCE_PATTERN = re.compile(r'^[A-Za-z0-9_-]{43}$')
VERIFIER_PATTERN = re.compile(r'^[A-Za-z0-9\-._~]{43,128}$')


def load_client(cur, client_id: str):
    cur.execute('SELECT * FROM oauth_clients WHERE client_id=%s AND enabled=true', (client_id,))
    item = cur.fetchone()
    if not item:
        raise HTTPException(400, 'invalid_client')
    return item


def authenticate_client(header: str | None):
    if not header or not header.startswith('Basic '):
        raise HTTPException(401, 'invalid_client', headers={'WWW-Authenticate': 'Basic realm="sso"'})
    try:
        from urllib.parse import unquote_plus
        raw = base64.b64decode(header[6:], validate=True).decode('utf-8')
        cid, secret = raw.split(':', 1)
        return unquote_plus(cid), unquote_plus(secret)
    except (ValueError, UnicodeDecodeError) as ex:
        raise HTTPException(401, 'invalid_client') from ex


@router.get('/.well-known/openid-configuration')
def discovery():
    i = get_settings().issuer.rstrip('/')
    return {
        'issuer': i,
        'authorization_endpoint': f'{i}/oauth/authorize',
        'token_endpoint': f'{i}/oauth/token',
        'userinfo_endpoint': f'{i}/oauth/userinfo',
        'revocation_endpoint': f'{i}/oauth/revoke',
        'jwks_uri': f'{i}/.well-known/jwks.json',
        'response_types_supported': ['code'],
        'grant_types_supported': ['authorization_code', 'refresh_token'],
        'subject_types_supported': ['public'],
        'id_token_signing_alg_values_supported': ['RS256'],
        'token_endpoint_auth_methods_supported': ['client_secret_basic'],
        'code_challenge_methods_supported': ['S256'],
        'scopes_supported': ['openid', 'profile'],
    }


@router.get('/.well-known/jwks.json')
def keys():
    return jwks()


@router.get('/oauth/authorize')
def authorize(request: Request, response_type: str, client_id: str, redirect_uri: str,
              scope: str, state: str, code_challenge: str, code_challenge_method: str,
              nonce: str | None = None):
    # This limited first-party provider supports only pre-approved confidential clients.
    with connection() as db:
        with db.cursor() as cur:
            client = load_client(cur, client_id)
            if (redirect_uri != client['redirect_uri'] or response_type != 'code'
                or code_challenge_method != 'S256' or not PKCE_PATTERN.fullmatch(code_challenge)
                or scope != 'openid profile' or not (16 <= len(state) <= 256)
                or (nonce is not None and not (16 <= len(nonce) <= 256))):
                raise HTTPException(400, 'Invalid authorization request')
            try:
                user = find_session(request.cookies.get('sso_sid'))
            except HTTPException:
                safe_return = request.url.path + '?' + request.url.query
                return RedirectResponse('/login?' + urlencode({'next': safe_return}), status_code=302)
            raw = random_token()
            cur.execute('''INSERT INTO oauth_authorization_codes
              (code_hash,user_id,client_id,redirect_uri,code_challenge,nonce,expires_at)
              VALUES (%s,%s,%s,%s,%s,%s,%s)''',
              (digest(raw), user['id'], client_id, redirect_uri, code_challenge, nonce,
               now_utc()+timedelta(seconds=120)))
    return RedirectResponse(redirect_uri + ('&' if '?' in redirect_uri else '?') + urlencode({'code': raw, 'state': state}), status_code=302)


@router.post('/oauth/token')
def token(authorization: str | None = Header(default=None),
          grant_type: str = Form(...), code: str | None = Form(None),
          redirect_uri: str | None = Form(None), code_verifier: str | None = Form(None),
          refresh_token: str | None = Form(None)):
    client_id, secret = authenticate_client(authorization)
    with connection() as db:
        with db.cursor() as cur:
            client = load_client(cur, client_id)
            if not safe_equals(client['client_secret_hash'], digest(secret)):
                raise HTTPException(401, 'invalid_client')

            if grant_type == 'authorization_code':
                if (not code or len(code)>256 or redirect_uri != client['redirect_uri']
                    or not code_verifier or not VERIFIER_PATTERN.fullmatch(code_verifier)):
                    raise HTTPException(400, 'invalid_grant')
                # Row lock + transaction ensures single-use codes across workers.
                cur.execute('SELECT * FROM oauth_authorization_codes WHERE code_hash=%s FOR UPDATE', (digest(code),))
                grant = cur.fetchone()
                if (not grant or grant['consumed_at'] or grant['expires_at'] <= now_utc()
                    or grant['client_id'] != client_id or grant['redirect_uri'] != redirect_uri
                    or not safe_equals(grant['code_challenge'], pkce_challenge(code_verifier))):
                    raise HTTPException(400, 'invalid_grant')
                cur.execute('UPDATE oauth_authorization_codes SET consumed_at=now() WHERE code_hash=%s', (digest(code),))
                user_id = grant['user_id']
                family_id = uuid4()
                nonce = grant['nonce']
            elif grant_type == 'refresh_token':
                if not refresh_token or len(refresh_token)>256:
                    raise HTTPException(400, 'invalid_grant')
                # Transaction-level advisory lock serializes rotation across family members.
                cur.execute('SELECT * FROM oauth_refresh_tokens WHERE token_hash=%s', (digest(refresh_token),))
                old = cur.fetchone()
                if not old or old['client_id'] != client_id:
                    raise HTTPException(400, 'invalid_grant')
                cur.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (str(old['family_id']),))
                cur.execute('SELECT * FROM oauth_refresh_tokens WHERE token_hash=%s FOR UPDATE', (digest(refresh_token),))
                old = cur.fetchone()
                if old['used_at'] or old['revoked_at'] or old['expires_at'] <= now_utc():
                    cur.execute('UPDATE oauth_refresh_tokens SET revoked_at=now() WHERE family_id=%s', (old['family_id'],))
                    # A 400 inside transaction rolls it back: commit revocation explicitly.
                    db.commit()
                    raise HTTPException(400, 'invalid_grant')
                cur.execute('UPDATE oauth_refresh_tokens SET used_at=now() WHERE token_hash=%s', (digest(refresh_token),))
                user_id = old['user_id']
                family_id = old['family_id']
                nonce = None
            else:
                raise HTTPException(400, 'unsupported_grant_type')

            cur.execute('SELECT is_active FROM app_users WHERE id=%s', (user_id,))
            u = cur.fetchone()
            if not u or not u['is_active']:
                raise HTTPException(400, 'invalid_grant')
            cur.execute('SELECT role FROM app_user_roles WHERE user_id=%s', (user_id,))
            roles = [r['role'] for r in cur.fetchall()]
            new_refresh = random_token()
            cur.execute('''INSERT INTO oauth_refresh_tokens
              (token_hash,family_id,user_id,client_id,expires_at) VALUES (%s,%s,%s,%s,%s)''',
              (digest(new_refresh), family_id, user_id, client_id,
               now_utc()+timedelta(days=get_settings().refresh_token_days)))
            access, identity = issue_tokens(user_id, client_id, client['audience'], roles, nonce)
    return {'access_token': access, 'id_token': identity, 'refresh_token': new_refresh,
            'token_type': 'Bearer', 'expires_in': get_settings().access_token_seconds,
            'scope': 'openid profile'}


@router.post('/oauth/revoke')
def revoke(authorization: str | None = Header(default=None), token: str = Form(...)):
    """Confidential-client refresh-token family revocation (RFC 7009-style)."""
    client_id, secret = authenticate_client(authorization)
    with connection() as db:
        with db.cursor() as cur:
            client = load_client(cur, client_id)
            if not safe_equals(client['client_secret_hash'], digest(secret)):
                raise HTTPException(401, 'invalid_client')
            cur.execute('SELECT family_id FROM oauth_refresh_tokens WHERE token_hash=%s AND client_id=%s', (digest(token), client_id))
            item = cur.fetchone()
            if item:
                cur.execute('UPDATE oauth_refresh_tokens SET revoked_at=now() WHERE family_id=%s AND client_id=%s', (item['family_id'],client_id))
    return {}


@router.get('/oauth/userinfo')
def userinfo(authorization: str | None = Header(default=None)):
    import jwt
    from .security import public_key
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Missing bearer token')
    try:
        claims = jwt.decode(authorization[7:], public_key(), algorithms=['RS256'],
                            issuer=get_settings().issuer, options={'verify_aud': False},
                            leeway=15)
        audience = claims.get('aud')
        with connection() as db:
            with db.cursor() as cur:
                cur.execute('SELECT 1 FROM oauth_clients WHERE audience=%s AND client_id=%s AND enabled=true',
                            (audience, claims.get('client_id')))
                if not cur.fetchone():
                    raise HTTPException(401, 'Invalid audience')
                cur.execute('SELECT id,display_name,is_active FROM app_users WHERE id=%s', (claims['sub'],))
                user = cur.fetchone()
                if not user or not user['is_active']:
                    raise HTTPException(401, 'Invalid user')
                return {'sub': str(user['id']), 'name': user['display_name']}
    except (jwt.PyJWTError, KeyError, ValueError) as ex:
        raise HTTPException(401, 'Invalid token') from ex
