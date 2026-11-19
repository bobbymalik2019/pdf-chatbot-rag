"""One-time bootstrapping; run from sso-service root, with .env configured."""
import getpass
import os
import re
import sys
from uuid import uuid4
from psycopg.errors import UniqueViolation
from sso_service.db import connection
from sso_service.security import hash_password, digest

mode = sys.argv[1] if len(sys.argv)>1 else ''
if mode == 'admin':
    email = input('Administrator email: ').strip().lower()
    display_name = input('Display name: ').strip()
    password = getpass.getpass('Strong password (at least 12 chars): ')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or not display_name or len(password)<12:
        raise SystemExit('Invalid email, display name or password')
    with connection() as db:
        with db.cursor() as c:
            c.execute('SELECT 1 FROM app_user_roles WHERE role=%s LIMIT 1', ('ADMIN',))
            if c.fetchone():
                raise SystemExit('An administrator already exists; use authenticated admin APIs')
            uid = uuid4()
            c.execute('INSERT INTO app_users (id,display_name) VALUES (%s,%s)', (uid, display_name))
            c.execute('INSERT INTO app_user_credentials (user_id,email,password_hash) VALUES (%s,%s,%s)', (uid,email,hash_password(password)))
            c.execute('INSERT INTO app_user_roles (user_id,role) VALUES (%s,%s)', (uid,'ADMIN'))
    print('Administrator provisioned successfully.')
elif mode == 'client':
    cid = input('Confidential client ID [pdf-chatbot]: ').strip() or 'pdf-chatbot'
    redirect = input('Exact callback URI [http://127.0.0.1:3000/auth/callback]: ').strip() or 'http://127.0.0.1:3000/auth/callback'
    audience = input('API audience [pdf-chatbot-api]: ').strip() or 'pdf-chatbot-api'
    secret = getpass.getpass('Client secret (generated externally, min 32 characters): ')
    if len(secret)<32 or not redirect.startswith(('https://','http://127.0.0.1:','http://localhost:')):
        raise SystemExit('Invalid client secret or redirect URI')
    with connection() as db:
        db.execute('INSERT INTO oauth_clients(client_id,client_secret_hash,redirect_uri,audience) VALUES (%s,%s,%s,%s)', (cid,digest(secret),redirect,audience))
    print('Registered confidential client. Store its secret in the consuming BFF environment.')
else:
    raise SystemExit('Usage: python scripts/bootstrap.py admin|client')
