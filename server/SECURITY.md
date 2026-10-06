# Security notes

## Why there is no request/response payload encryption

The original plan called for AES-256-GCM encryption of every request and
response body, on top of HTTPS. That was deliberately **not** built. Here is the
reasoning, so the decision is easy to revisit.

To decrypt a response, the browser needs the key. Anything the browser knows is
readable by whoever controls the browser: the key would sit in the JavaScript
bundle, visible to anyone who opens DevTools or downloads the bundle. An
attacker who can read network traffic can equally read the bundle, so the
encryption stops nobody.

Meanwhile it costs:

- Every request and response becomes opaque in DevTools and in server logs.
- The automatic API docs at `/docs` stop working against a live server.
- Streaming (`/messages/stream`), file uploads and PDF downloads each need a
  carve-out, so parts of the API end up unencrypted anyway.
- Every bug report becomes harder to diagnose.

Payload encryption *is* worth it when the key does not live in the client — for
example end-to-end encryption where only two users hold keys and the server is
untrusted. This app's server reads every document in order to answer questions
about it, so that model does not apply here.

**Transport security is TLS's job.** Terminate HTTPS at the host or reverse proxy
and set `COOKIE_SECURE=True` (see below).

## What is in place instead

| Protection | Where |
|---|---|
| Password hashing (bcrypt) | `app/core/security.py` |
| JWT access tokens, short-lived | `app/core/security.py` |
| Refresh token in an httpOnly cookie, never readable by JS | `app/routers/auth.py` |
| Logout revokes both tokens via a Redis blacklist | `app/routers/auth.py` |
| Per-user rate limits on AI calls and uploads; per-IP on registration | `app/core/rate_limit.py` |
| Security headers on every response | `app/core/security_headers.py` |
| Strict CORS allowlist with explicit methods and headers | `app/main.py` |
| Every query scoped to the owning user | routers + services |
| Upload validation: type, magic bytes, size cap | `app/routers/pdfs.py` |
| Account deletion re-checks the password | `app/routers/users.py` |

## Before deploying

1. **Serve over HTTPS** and set `COOKIE_SECURE=True` in `.env`, so the refresh
   cookie is never sent over plain HTTP.
2. **Set `DEBUG=False`**, which also turns on the `Strict-Transport-Security`
   header and silences SQL echo.
3. **Rotate `JWT_SECRET_KEY`** to a long random value; every existing session is
   invalidated when it changes.
4. **Set `ALLOWED_ORIGINS`** to the real frontend origin only.
5. **Keep `.env` out of git.** It is listed in `.gitignore`; note that keys
   committed before that was added still exist in the repository history.

## Known gaps

- Email verification and password reset are not implemented.
- Uploaded PDFs are stored unencrypted on local disk.
- Rate limits fail open: if Redis is down, requests are allowed through. This is
  a deliberate availability trade-off.
