# Charter26 SSO + PDF Chatbot — Diagnostic Helpers

**Environment:** Windows PowerShell 5.1+, Node.js (supports `--env-file`), and `pg` installed in `Proposed-Solution/chatbot-gateway`.

These scripts are **local diagnostics**, not application features. They do not change the database or application configuration. They avoid printing plaintext passwords, session cookies, tokens, and OIDC state/nonce values.

## Starting location

Open PowerShell in `Proposed-Solution/chatbot-gateway`. Copy this folder inside the gateway as `diagnostics` (keep it untracked if desired). Then run:

```powershell
node --env-file=.env .\diagnostics\diagnose.cjs env
```

Shows connection settings, whether a password is configured, and its length (not its value).

## Diagnose password mismatch (the November 19 incident)

```powershell
.\diagnostics\Test-EnvOverrides.ps1
.\diagnostics\Compare-DbPassword.ps1
```

The second script securely prompts for the expected password and compares its SHA256 digest with the password Node loads from `.env`. **Only a true/false match is printed.** Works on Windows PowerShell 5.1. If the values differ, check quoted passwords containing `#`, whitespace, or inherited environment variables. For example, set `CHATBOT_DB_PASSWORD="<existing-password>"` in your private `.env`, using your real password (never paste it in chat).

PowerShell script policy may require launching via `powershell -NoProfile -ExecutionPolicy Bypass -File .\diagnostics\Compare-DbPassword.ps1` where permitted by your organization.

## Test PostgreSQL authentication via Node

```powershell
node --env-file=.env .\diagnostics\diagnose.cjs db
```

Expected: `CONNECTED {"db_user":"rag_user","db_name":"rag_db"}`. An SQLSTATE `28P01` indicates PostgreSQL rejected the credentials; the previous issue was a truncated 17-character password instead of the intended 20-character password due to `.env` parsing.

## Verify session persistence (without printing session contents)

```powershell
node --env-file=.env .\diagnostics\diagnose.cjs sessions
```

Counts stored sessions and sessions with an `oidcTransaction` JSON key. It explicitly casts `sess::jsonb` because the `chatbot_sessions.sess` column is `json`, not `jsonb`.

Equivalent SQL in pgAdmin:

```sql
SELECT expire, sess::jsonb ? 'oidcTransaction' AS has_oidc_transaction
FROM public.chatbot_sessions
ORDER BY expire DESC LIMIT 5;
```

## Check `/auth/login` without leaking secrets

```powershell
.\diagnostics\Test-OidcLogin.ps1
```

Expected: `HTTP/1.1 302 Found`, redirect path `/oauth/authorize` on `ssotest.charter26.com`, and all required parameter names present. This script intentionally does **not** show raw `Location` or `Set-Cookie` headers.

## Additional one-liners

```powershell
# Caddy HTTPS listener
Get-NetTCPConnection -LocalPort 443 -State Listen

# Chatbot and SSO Gateway listeners
Get-NetTCPConnection -LocalPort 3000,3100 -State Listen

# Inspect the latest Ollama log entries
Get-Content "$env:LOCALAPPDATA\Ollama\server.log" -Tail 50

# Check Git ignore rule matches (run from repo root)
git check-ignore -v Proposed-Solution/pdf-ingestion-service/storage/

# Check staged patch whitespace (not a compilation check)
git diff --cached --check
```

## Safety reminders

- Never paste full `Location:` URLs, `Set-Cookie:` headers, passwords, token claims, or digest output into chats/issues.
- A password hash can facilitate offline guesses; this toolkit keeps the computed hashes in memory and only displays match/no-match.
- `--ssl-no-revoke` is for local Windows curl certificate-revocation diagnostics; it is not a substitute for trusting the mkcert CA. Do not use `--insecure` for application connections.
- Ensure `.env` and any locally stored password notes remain ignored by Git.
- Remove or invalidate disclosed test sessions before sensitive login testing.
