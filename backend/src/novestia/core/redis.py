"""Redis client and FastAPI dependency."""

from __future__ import annotations

from collections.abc import AsyncIterator

import redis.asyncio as aioredis

from novestia.config import settings

_redis_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    """Get or create the global Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _redis_client


async def get_redis() -> AsyncIterator[aioredis.Redis]:
    """FastAPI dependency that yields a Redis client."""
    yield get_redis_client()


async def close_redis() -> None:
    """Close the Redis connection. Called on app shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
