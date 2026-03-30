"""
Redis-backed cache for proxied HTTP responses (GET only).
"""

from __future__ import annotations

import base64
import json
from typing import Any

from ..db import redis_manager

CACHE_PREFIX = "caching_proxy:v1:"


def cache_key(method: str, url: str) -> str:
    return f"{CACHE_PREFIX}{method.upper()}:{url}"


async def get_cached(key: str) -> dict[str, Any] | None:
    raw = await redis_manager.client.get(key)
    if raw is None:
        return None
    data = json.loads(raw)
    data["body"] = base64.b64decode(data.pop("body_b64"))
    return data


async def set_cached(
    key: str,
    status_code: int,
    headers: dict[str, str],
    body: bytes,
) -> None:
    payload = {
        "status_code": status_code,
        "headers": headers,
        "body_b64": base64.b64encode(body).decode("ascii"),
    }
    await redis_manager.client.set(key, json.dumps(payload))


async def clear_proxy_cache() -> int:
    """Delete all keys used by the caching proxy. Returns number of keys removed."""
    deleted = 0
    cursor: int | str = 0
    while True:
        cursor, keys = await redis_manager.client.scan(
            cursor=cursor, match=f"{CACHE_PREFIX}*", count=200
        )
        if keys:
            deleted += int(await redis_manager.client.delete(*keys))
        if cursor in (0, "0"):
            break
    return deleted
