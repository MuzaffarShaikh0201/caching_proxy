"""
Poetry scripts: API server and caching-proxy CLI.
"""

import argparse
import asyncio
import os

import uvicorn


def api():
    parser = argparse.ArgumentParser(description="Run API server")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Run API in local development mode",
    )

    args = parser.parse_args()

    if args.local:
        uvicorn.run(
            "src.main:app",
            host="localhost",
            port=5000,
            reload=True,
        )
    else:
        uvicorn.run(
            "src.main:app",
            host="0.0.0.0",
            port=5000,
        )


async def _clear_cache_async() -> None:
    from src.db.redis_client import redis_manager
    from src.services.proxy_cache import clear_proxy_cache

    await redis_manager.init()
    try:
        removed = await clear_proxy_cache()
        print(f"Cleared {removed} cache entries.")
    finally:
        await redis_manager.close()


def caching_proxy() -> None:
    parser = argparse.ArgumentParser(
        description="Start the caching proxy or clear its Redis cache.",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Port for the caching proxy server.",
    )
    parser.add_argument(
        "--origin",
        type=str,
        help="Origin base URL to forward requests to (e.g. https://dummyjson.com).",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear all cached proxy responses in Redis and exit.",
    )

    args = parser.parse_args()

    if args.clear_cache:
        if args.port is not None or args.origin is not None:
            parser.error("--clear-cache cannot be used with --port or --origin")
        asyncio.run(_clear_cache_async())
        return

    if args.port is None or args.origin is None:
        parser.error("--port and --origin are required unless using --clear-cache")

    os.environ["PROXY_ORIGIN"] = args.origin.rstrip("/")

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=args.port,
    )
