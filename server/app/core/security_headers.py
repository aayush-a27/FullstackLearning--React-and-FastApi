"""
Security response headers.

These replace the payload-level AES encryption in the original plan. That scheme
would have shipped the shared key inside the browser bundle, where anyone can
read it, so it added no real protection over TLS while breaking DevTools and the
API docs. See SECURITY.md for the full reasoning.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Applied to every response
BASE_HEADERS = {
    # Don't let browsers second-guess declared content types
    "X-Content-Type-Options": "nosniff",
    # The app is never meant to be framed
    "X-Frame-Options": "DENY",
    # Don't leak the full URL (which contains chat ids) to third-party sites
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # This API has no need for these device features
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), interest-cohort=()",
}

# Only meaningful over HTTPS, so it's added when not in debug
HSTS_HEADER = ("Strict-Transport-Security", "max-age=31536000; includeSubDomains")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach security headers to every response."""

    def __init__(self, app: ASGIApp, *, production: bool):
        super().__init__(app)
        self.production = production

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        for header, value in BASE_HEADERS.items():
            response.headers.setdefault(header, value)
        if self.production:
            name, value = HSTS_HEADER
            response.headers.setdefault(name, value)
        return response
