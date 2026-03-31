"""
Redis client utility — optional infrastructure.
All features that need Redis degrade gracefully when REDIS_URL is not configured.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_redis_client = None


async def get_redis():
    """
    Return a connected Redis client, or None if Redis is unconfigured/unreachable.
    The client is a module-level singleton — safe for use across async contexts.
    """
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    from app.core.config import settings
    if not settings.REDIS_URL:
        return None

    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        _redis_client = client
        logger.info("Redis connected: %s", settings.REDIS_URL)
        return _redis_client
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — continuing without caching/locks.", exc)
        return None


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


async def acquire_lock(lock_key: str, ttl: int = 300) -> bool:
    """
    Acquire a distributed lock via Redis SET NX.
    Returns True if the lock was acquired, False if already held.
    Falls back to True (no-op lock) when Redis is unavailable.
    """
    redis = await get_redis()
    if redis is None:
        return True  # No Redis → single-instance mode, always proceed
    acquired = await redis.set(lock_key, "1", nx=True, ex=ttl)
    return bool(acquired)


async def release_lock(lock_key: str) -> None:
    redis = await get_redis()
    if redis is not None:
        await redis.delete(lock_key)
