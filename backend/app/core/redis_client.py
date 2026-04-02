"""
Redis client utility — optional infrastructure.
All features that need Redis degrade gracefully when REDIS_URL is not configured.
"""
import logging
import json
from typing import Optional, Any
from datetime import timedelta

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
        # 优化连接配置
        client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5.0,  # 5s 连接超时
            socket_timeout=5.0,          # 5s 操作超时
            max_connections=50,          # 最大连接数
            retry_on_timeout=True,       # 超时自动重试
        )
        await client.ping()  # type: ignore[misc]
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


async def cache_get(key: str) -> Optional[Any]:
    """从 Redis 获取缓存数据，自动反序列化 JSON"""
    redis = await get_redis()
    if redis is None:
        return None
    try:
        data = await redis.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning(f"Redis cache get failed for {key}: {e}")
    return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    """
    设置缓存数据，自动序列化 JSON
    :param key: 缓存键
    :param value: 缓存值 (任意可 JSON 序列化类型)
    :param ttl_seconds: 过期时间 (秒)，默认 5 分钟
    """
    redis = await get_redis()
    if redis is None:
        return False
    try:
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        await redis.setex(key, timedelta(seconds=ttl_seconds), serialized)
        return True
    except Exception as e:
        logger.warning(f"Redis cache set failed for {key}: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """删除缓存"""
    redis = await get_redis()
    if redis is None:
        return False
    try:
        await redis.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Redis cache delete failed for {key}: {e}")
        return False


async def cache_delete_pattern(pattern: str) -> int:
    """
    批量删除匹配模式的缓存键
    :param pattern: 匹配模式 (如 "analysis:*")
    :return: 删除的键数量
    """
    redis = await get_redis()
    if redis is None:
        return 0
    try:
        keys = []
        async for key in redis.scan_iter(pattern):
            keys.append(key)
        if keys:
            return await redis.delete(*keys)
    except Exception as e:
        logger.warning(f"Redis cache delete pattern failed for {pattern}: {e}")
    return 0
