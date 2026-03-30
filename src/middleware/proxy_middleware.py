"""
HTTP middleware: forwards traffic to the configured origin except for app routes.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..services.proxy_service import proxy_request

# App routes that must not be proxied (FastAPI docs, OpenAPI, health)
_EXCLUDED_PATHS = frozenset(
    {
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
    }
)


def _is_excluded(path: str) -> bool:
    if path in _EXCLUDED_PATHS:
        return True
    if path.startswith("/docs") or path.startswith("/redoc"):
        return True
    return False


class ProxyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if _is_excluded(request.url.path):
            return await call_next(request)
        return await proxy_request(request)
