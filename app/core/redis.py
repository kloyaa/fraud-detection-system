"""Async Redis client for caching, idempotency keys, and velocity counters.

Uses redis.asyncio for non-blocking I/O. Client is initialized once at startup
via lifespan and injected via FastAPI Depends(get_redis).

Per ADR-006: Redis sliding window counters require sub-ms atomic operations.
"""

from typing import AsyncGenerator

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis: Redis | None = None  # type: ignore[type-arg]


async def init_redis() -> Redis:  # type: ignore[type-arg]
    """Initialize the Redis connection pool at application startup.

    Called from the FastAPI lifespan context manager.
    Verifies connectivity with a PING before yielding control.

    Returns:
        Initialized Redis client with connection pool.

    Raises:
        ConnectionError: If Redis is unreachable at startup.
    """
    global _redis
    _redis = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
    )
    await _redis.ping()
    logger.info("redis_connected", url=settings.redis_url)
    return _redis


async def close_redis() -> None:
    """Close Redis connection pool at application shutdown."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("redis_disconnected")


async def get_redis() -> AsyncGenerator[Redis, None]:  # type: ignore[type-arg]
    """FastAPI dependency — inject Redis client into route handlers.

    Usage:
        from redis.asyncio import Redis
        from fastapi import Depends
        from app.core.redis import get_redis

        @router.post("/endpoint")
        async def handler(redis: Redis = Depends(get_redis)):
            await redis.set("key", "value", ex=86400)

    Yields:
        Active Redis client (shared pool — do NOT close it in the handler).
    """
    assert _redis is not None, "Redis not initialized — check app lifespan startup"
    yield _redis
