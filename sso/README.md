# Sentinel SSO — Standalone Identity Platform

A multi-service, production-*oriented* SSO development baseline:

| Layer | Location | Role |
| --- | --- | --- |
| React/Vite | `frontend/` | Independent login + administration portal with React Router |
| Express | `gateway/` | **Serves the compiled React UI** and proxies same-origin `/api`, `/oauth`, `/.well-known` |
| FastAPI | `service/` | Identity management, credential verification, OAuth authorization and token services |
| PostgreSQL | `database/migrations/` | Separate SSO database; no changes to PDF Chatbot database |

**Status:** This is an **unreviewed reference implementation / development starter**, not a certified or production-ready OpenID Connect provider. It implements a narrow pre-approved confidential-client authorization-code flow with PKCE, RSA-signed JWTs, opaque refresh tokens with rotation, basic admin endpoints, and login sessions. Before any real deployment, use a vetted, standards-compliant authorization-server implementation or subject this implementation to interoperability testing, threat modeling, penetration testing, and independent security review. Do not place it on the public internet as-is.

## Architecture

```text
Browser  http://127.0.0.1:3100
  ├── React routes: /login /dashboard /users /sessions
  └── Express gateway :3100 (same origin; serves React dist)
       ├── /api/*          ──► FastAPI :8100
       ├── /oauth/*        ──► FastAPI :8100
       └── /.well-known/*  ──► FastAPI :8100
                                   └── PostgreSQL sso_db

PDF Chatbot (separate existing app)
  Browser → Chatbot BFF :3000 → PDF FastAPI :8000
  Login redirects to :3100/oauth/authorize; Chatbot BFF exchanges code,
  holds refresh+access tokens server-side, and forwards access JWT to PDF API.
```

**Independent identity ownership:** SSO `app_users.id` is the canonical `sub` UUID. Chatbot retains its existing `app_users.id`, and maps `app_users.external_user_id = SSO sub`. Keep project `owner_id` pointing at the local Chatbot user UUID. Do not overwrite existing Chatbot user IDs.

## Requirements

- Python 3.11+ with `uv` or pip; Node.js 20.19+ and npm; PostgreSQL 15+.
- Install/build dependencies locally; `node_modules`, `.venv`, key material, `.env`, and `dist` are not committed.
- The existing three auth tables in the *Chatbot* database are not used by the standalone SSO. Create the tables in **its own `sso_db`**. Do not delete the existing tables until a later migration plan is agreed.

## 1. Database

Create a dedicated PostgreSQL database and login role with access only to SSO tables. For an initial local lab, create `sso_db` and a role `sso_app` using pgAdmin or psql, then execute:

```bash
psql -h 127.0.0.1 -U sso_app -d sso_db -v ON_ERROR_STOP=1 -f database/migrations/001_sso.sql
```

Use a database owner/migration account with CREATE TABLE privileges; the runtime SSO database role should later have only necessary table privileges. `app_users` is created afresh in this **independent SSO database**. Existing Chatbot records are not migrated or altered here.

## 2. Python identity service

From `service/`:

```powershell
Copy-Item .env.example .env
# Edit DATABASE_URL and confirm ISSUER/PUBLIC_ORIGIN match http://127.0.0.1:3100
uv sync --extra test
uv run python scripts/generate_keys.py
uv run python scripts/bootstrap.py admin
# First add your approved confidential client after creating its 32+-character secret:
uv run python scripts/bootstrap.py client
uv run python -m pytest -q
uv run python -m uvicorn sso_service.main:app --host 127.0.0.1 --port 8100
```

If using a traditional virtual environment, use `pip install -e '.[test]'` then run scripts with `python`. Ensure the project is installed so `sso_service` imports resolve.

**Client registration:** For the PDF Chatbot proof-of-concept, register `client_id=pdf-chatbot`, `redirect_uri=http://127.0.0.1:3000/auth/callback`, and audience `pdf-chatbot-api`. Supply a securely generated 32+-character secret and store it **only** in the Chatbot BFF server environment. SSO stores its SHA-256 hash, not the secret. This starter supports one exact redirect URI per client.

## 3. React production build (required even on first run)

From `frontend/`:

```powershell
npm install
npm run build
```

**Do not start the Vite dev server for the integrated setup.** Build output is `frontend/dist/`.

## 4. Express gateway hosts React + proxies Python

From `gateway/`:

```powershell
npm install
$env:PORT='3100'
$env:SSO_PYTHON_ORIGIN='http://127.0.0.1:8100'
npm start
```

Browse **http://127.0.0.1:3100/login**. Express serves the compiled Vite application and forwards the SSO API/OAuth endpoints to Python on port 8100. Both the React UI and OAuth issuer use the same origin. **Use the exact hostname `127.0.0.1` rather than switching between it and `localhost`**, as login CSRF checks intentionally require an exact origin.

## 5. Smoke tests

1. `GET http://127.0.0.1:8100/healthz` → `{"status":"ok","service":"sso"}`.
2. `GET http://127.0.0.1:3100/.well-known/openid-configuration` → discovery JSON.
3. `GET http://127.0.0.1:3100/.well-known/jwks.json` → RSA public key.
4. `GET http://127.0.0.1:3100/login` → React page served by Express (not Vite).
5. Login as bootstrapped admin. Navigate to **Users & Roles**. Create a USER and inspect role assignment.
6. Start an authorization-code request for a **registered** confidential client. It must redirect to login if needed, then return to its registered callback with a code and state. Use S256 verifier and client-secret authentication to redeem code at `/oauth/token`.
7. Check returned access JWT `iss`, `aud`, `exp`, `sub` and `roles`. Confirm an authorization code cannot be redeemed twice.
8. Use `/oauth/token` refresh grant, confirm rotation, and confirm reuse of an old refresh token revokes its token family.

### Example authorization URL generator (for a registered client)

Use the supplied `examples/make_authorize_url.py`; it prints a browser URL and PKCE verifier. It does not implement the consuming Chatbot BFF callback.

## Security boundaries and production readiness

The included controls are intentionally scoped. **Before exposing to actual users**, complete:

- Standards-compliance review of OIDC/OAuth error handling, client registration, consent, logout, metadata, and interoperability. Use an audited authorization server for real public deployments.
- TLS termination and HTTPS-only origins; set `SECURE_COOKIES=true`, use HSTS through the trusted TLS edge, restrict host/proxy trust, and protect signing keys in an external secrets manager/HSM where appropriate.
- Persistent distributed login throttling and lockout/risk controls (the starter has no brute-force throttling), abuse prevention and CAPTCHA/risk policies if public registration is added.
- Session cookie policy, token replay tests, credential update/recovery, account disablement, admin audit log, MFA and security notifications.
- Complete refresh family risk handling and back-channel logout/SSO session revocation across consuming apps; local JWT validation cannot immediately revoke previously issued access tokens.
- Key rotation and key overlap with an explicit `kid` rollover plan; backups, monitoring, request tracing, alerts, vulnerability scanning, and dependency pinning/patching.
- Restrict database runtime permissions, encrypt backups, and add automated integration/contract tests against a running PostgreSQL instance and OIDC RP client.
- Do not treat React route guards as authorization. Python enforces roles and resource access.
- SSO React receives no JWT or refresh token. Existing Chatbot BFF **must be extended** with an OIDC client and encrypted server-side session store; it is not yet implemented in this standalone SSO package.

## Components currently implemented

- Bootstrap admin, admin-only account creation and role changes.
- Session cookies, CSRF token validation for mutation endpoints, authenticated profile.
- Pre-registered confidential clients, exact redirect URI matching, `state`, PKCE S256.
- Single-use authorization codes (120-second expiry), RSA-signed access and ID JWTs, JWKS and basic discovery metadata.
- Opaque refresh-token rotation with a token-family replay revocation path; client-authenticated revoke endpoint.
- React Router layout and pages; Express serves the built UI at initial startup.

## Next integration task: PDF Chatbot

Implement OIDC client logic in the **existing Chatbot Express BFF**, preferably using an established OIDC client library, with:

1. Login redirect + cryptographic `state`, `nonce`, PKCE storage in a short-lived BFF transaction.
2. Code exchange at SSO token endpoint via confidential client authentication.
3. Encrypted or appropriately protected server-side session store (e.g. Redis), **never** access/refresh tokens in browser storage.
4. Only opaque `HttpOnly; Secure; SameSite=Lax` browser session cookie; CSRF checks on cookie-authenticated state changes.
5. Serialize refresh for the same session to avoid reuse/replay during concurrent requests.
6. Forward access JWT to PDF FastAPI, which validates `kid`/JWKS, allowed algorithm, issuer, audience, expiry, and `sub`; map `sub` to Chatbot `app_users.external_user_id`.
7. Logout revokes refresh token, clears BFF session, and handles SSO global logout policy separately.

Never use user-supplied `owner_id` in trusted authorization decisions. Existing project ownership still belongs in Chatbot FastAPI.
