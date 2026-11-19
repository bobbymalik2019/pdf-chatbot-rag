import re
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from psycopg.errors import UniqueViolation
from .db import connection
from .models import LoginRequest, NewUser, RoleChange
from .security import hash_password, verify_password, random_token, digest, safe_equals
from .settings import get_settings

router = APIRouter(prefix='/api/v1')
COOKIE = 'sso_sid'
CSRF_COOKIE = 'sso_csrf'


def now_utc():
    return datetime.now(timezone.utc)


def browser_origin(request: Request):
    origin = request.headers.get('origin')
    if origin != get_settings().public_origin:
        raise HTTPException(403, 'Request origin not permitted')


def csrf_guard(request: Request):
    browser_origin(request)
    cookie = request.cookies.get(CSRF_COOKIE, '')
    header = request.headers.get('x-csrf-token', '')
    if not cookie or not header or not safe_equals(cookie, header):
        raise HTTPException(403, 'CSRF validation failed')


def find_session(raw: str | None):
    if not raw:
        raise HTTPException(401, 'Authentication required')
    with connection() as db:
        with db.cursor() as cur:
            cur.execute('''SELECT u.id, u.display_name, u.is_active FROM auth_sessions s
              JOIN app_users u ON u.id=s.user_id
              WHERE s.token_hash=%s AND s.revoked_at IS NULL AND s.expires_at>now()''', (digest(raw),))
            user = cur.fetchone()
            if not user or not user['is_active']:
                raise HTTPException(401, 'Authentication required')
            cur.execute('SELECT role FROM app_user_roles WHERE user_id=%s', (user['id'],))
            user['roles'] = [r['role'] for r in cur.fetchall()]
            return user


def current_user(sso_sid: str | None = Cookie(default=None)):
    return find_session(sso_sid)


def admin(user=Depends(current_user)):
    if 'ADMIN' not in user['roles']:
        raise HTTPException(403, 'Administrator role required')
    return user


def set_cookie(response: Response, name: str, value: str, *, http_only: bool, max_age: int):
    response.set_cookie(
        name, value, max_age=max_age, httponly=http_only,
        secure=get_settings().secure_cookies, samesite='lax', path='/'
    )


@router.get('/auth/csrf')
def csrf(response: Response):
    token = random_token()
    set_cookie(response, CSRF_COOKIE, token, http_only=False, max_age=8 * 3600)
    return {'csrf_token': token}


@router.post('/auth/login', dependencies=[Depends(csrf_guard)])
def login(payload: LoginRequest, response: Response):
    # Use generic failure messages and verify a dummy hash to limit username enumeration.
    dummy = '$argon2id$v=19$m=65536,t=3,p=4$MTIzNDU2Nzg5MDEyMzQ1Ng$Cct4LtxRlLClEGPVvZVmNT5GuNnzvRuDTBrNSokN9sY'
    email = payload.email.strip().lower()
    with connection() as db:
        with db.cursor() as cur:
            cur.execute('''SELECT u.id, u.is_active, c.password_hash FROM app_user_credentials c
              JOIN app_users u ON u.id=c.user_id WHERE lower(c.email)=%s''', (email,))
            user = cur.fetchone()
            if not user:
                verify_password(payload.password, dummy)
            if not user or not user['is_active'] or not verify_password(payload.password, user['password_hash']):
                raise HTTPException(401, 'Invalid email or password')
            raw = random_token()
            cur.execute('''INSERT INTO auth_sessions(id,user_id,token_hash,expires_at)
              VALUES (%s,%s,%s,%s)''', (uuid4(), user['id'], digest(raw), now_utc()+timedelta(hours=get_settings().session_hours)))
    set_cookie(response, COOKIE, raw, http_only=True, max_age=get_settings().session_hours*3600)
    return {'authenticated': True}


@router.get('/auth/me')
def me(user=Depends(current_user)):
    return {'id': str(user['id']), 'display_name': user['display_name'], 'roles': user['roles']}


@router.post('/auth/logout', dependencies=[Depends(csrf_guard)])
def logout(response: Response, sso_sid: str | None = Cookie(default=None)):
    if sso_sid:
        with connection() as db:
            db.execute('UPDATE auth_sessions SET revoked_at=now() WHERE token_hash=%s', (digest(sso_sid),))
    response.delete_cookie(COOKIE, path='/')
    return {'authenticated': False}


@router.get('/admin/users')
def list_users(_=Depends(admin)):
    with connection() as db:
        with db.cursor() as cur:
            cur.execute('''SELECT u.id,u.display_name,u.is_active,c.email,
            COALESCE(array_agg(r.role) FILTER(WHERE r.role IS NOT NULL),'{}') AS roles
            FROM app_users u JOIN app_user_credentials c ON c.user_id=u.id
            LEFT JOIN app_user_roles r ON r.user_id=u.id
            GROUP BY u.id,c.email ORDER BY u.created_at DESC''')
            return [{**u, 'id': str(u['id'])} for u in cur.fetchall()]


@router.post('/admin/users', status_code=201, dependencies=[Depends(csrf_guard)])
def create_user(payload: NewUser, _=Depends(admin)):
    email = payload.email.strip().lower()
    roles = set(payload.roles)
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or not roles or not roles <= {'ADMIN','USER'}:
        raise HTTPException(422, 'Invalid email or roles')
    try:
        with connection() as db:
            with db.cursor() as cur:
                user_id = uuid4()
                cur.execute('INSERT INTO app_users(id, display_name) VALUES (%s,%s)', (user_id,payload.display_name.strip()))
                cur.execute('INSERT INTO app_user_credentials(user_id,email,password_hash) VALUES (%s,%s,%s)',
                            (user_id, email, hash_password(payload.password)))
                for role in roles:
                    cur.execute('INSERT INTO app_user_roles(user_id,role) VALUES (%s,%s)', (user_id,role))
        return {'id': str(user_id)}
    except UniqueViolation as ex:
        raise HTTPException(409, 'Unable to create account') from ex


@router.put('/admin/users/{user_id}/roles', dependencies=[Depends(csrf_guard)])
def change_roles(user_id: str, payload: RoleChange, operator=Depends(admin)):
    from uuid import UUID
    try:
        uid = UUID(user_id)
    except ValueError as ex:
        raise HTTPException(422, 'Invalid user ID') from ex
    roles = set(payload.roles)
    if not roles <= {'ADMIN','USER'}:
        raise HTTPException(422, 'Unsupported role')
    if uid == operator['id'] and 'ADMIN' not in roles:
        raise HTTPException(409, 'Cannot remove your own administrator role')
    with connection() as db:
        with db.cursor() as cur:
            cur.execute('SELECT id FROM app_users WHERE id=%s FOR UPDATE', (uid,))
            if not cur.fetchone():
                raise HTTPException(404, 'User not found')
            cur.execute('DELETE FROM app_user_roles WHERE user_id=%s', (uid,))
            for role in roles:
                cur.execute('INSERT INTO app_user_roles(user_id,role) VALUES (%s,%s)', (uid,role))
    return {'id': str(uid), 'roles': sorted(roles)}
