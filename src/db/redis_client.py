from typing import Optional
from redis.asyncio import Redis
import redis.asyncio as aioredis
from redis.exceptions import RedisError

from ..config import settings


class RedisManager:
    """
    Redis connection manager for the Caching Proxy.
    """

    def __init__(self):
        self._client: Optional[Redis] = None

    async def init(self) -> None:
        """Initialize Redis connection pool."""
        self._client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def close(self) -> None:
        """Close Redis connections."""
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> Redis:
        """Get Redis client instance."""
        if self._client is None:
            raise RuntimeError("RedisManager not initialized. Call init() first.")
        return self._client

    async def ping(self) -> bool:
        """
        Ping Redis to check connection.

        Returns:
            True if connected, False otherwise
        """
        try:
            return await self.client.ping()
        except RedisError:
            return False


redis_manager = RedisManager()
