"""
Forward HTTP requests to the configured origin and integrate Redis caching.
"""

from __future__ import annotations

import httpx
from starlette.requests import Request
from starlette.responses import Response

from ..config import settings
from ..utils.logging import get_logger
from . import proxy_cache

logger = get_logger(__name__)

# RFC 7230 hop-by-hop headers — do not forward or store
HOP_BY_HOP_REQUEST = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "host",
    }
)

HOP_BY_HOP_RESPONSE = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
)

CACHEABLE_METHODS = frozenset({"GET"})


def _build_target_url(path: str, query: str) -> str:
    origin = (settings.proxy_origin or "").rstrip("/")
    p = path or "/"
    if not p.startswith("/"):
        p = f"/{p}"
    target = f"{origin}{p}"
    if query:
        target = f"{target}?{query}"
    return target


def _filter_request_headers(request: Request) -> dict[str, str]:
    out: dict[str, str] = {}
    for name, value in request.headers.items():
        if name.lower() in HOP_BY_HOP_REQUEST:
            continue
        out[name] = value
    return out


def _filter_response_headers(headers: httpx.Headers) -> dict[str, str]:
    out: dict[str, str] = {}
    for name, value in headers.items():
        ln = name.lower()
        if ln in HOP_BY_HOP_RESPONSE:
            continue
        if ln == "content-length":
            continue
        out[name] = value
    return out


async def proxy_request(request: Request) -> Response:
    if not settings.proxy_origin:
        return Response(
            content=b'{"detail":"Caching proxy origin is not configured."}',
            status_code=503,
            media_type="application/json",
        )

    method = request.method.upper()
    path = request.url.path
    query = request.url.query or ""
    target_url = _build_target_url(path, query)

    cache_key_str: str | None = None
    if method in CACHEABLE_METHODS:
        cache_key_str = proxy_cache.cache_key(method, target_url)
        cached = await proxy_cache.get_cached(cache_key_str)
        if cached is not None:
            headers = dict(cached["headers"])
            headers["X-Cache"] = "HIT"
            return Response(
                content=cached["body"],
                status_code=cached["status_code"],
                headers=headers,
            )

    req_headers = _filter_request_headers(request)
    body = await request.body() if method in ("POST", "PUT", "PATCH", "DELETE") else None

    timeout = httpx.Timeout(60.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            upstream = await client.request(
                method,
                target_url,
                headers=req_headers,
                content=body if body else None,
            )
        except httpx.RequestError as e:
            logger.error("Upstream request failed: %s", e)
            return Response(
                content=b'{"detail":"Failed to reach origin server."}',
                status_code=502,
                media_type="application/json",
            )

    resp_headers = _filter_response_headers(upstream.headers)
    resp_headers["X-Cache"] = "MISS"
    content = upstream.content

    if (
        cache_key_str
        and method in CACHEABLE_METHODS
        and upstream.status_code == 200
    ):
        to_store = dict(resp_headers)
        to_store.pop("X-Cache", None)
        await proxy_cache.set_cached(
            cache_key_str,
            upstream.status_code,
            to_store,
            content,
        )

    return Response(
        content=content,
        status_code=upstream.status_code,
        headers=resp_headers,
    )
