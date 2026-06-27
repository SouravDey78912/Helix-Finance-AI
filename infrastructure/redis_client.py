"""
infrastructure/redis_client.py
================================
Async Redis client.

Local:       Redis in Docker Compose (free)
Production:  Redis Cluster / Redis Enterprise

Use cases in this platform:
  - Rate limiter counters
  - JWT refresh token revocation list
  - Celery result backend
  - Response caching (optional)

Migration path: Update REDIS_URL env var only — no code changes.

TODO: Add connection pool settings.
TODO: Implement key prefix namespacing per feature.
"""

import redis.asyncio as aioredis
import structlog

from apps.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

_redis_client: aioredis.Redis | None = None


async def get_redis_client() -> aioredis.Redis:
    """
    Return the shared async Redis client (lazy-initialised).

    TODO: Add health check / reconnection logic.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("Redis client initialised", url=settings.redis_url)
    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection on app shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis client closed")
