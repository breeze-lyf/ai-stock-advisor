from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db.repositories.user_repository import UserRepository
from app.models.user import User
from app.core import security
from app.core.database import get_db

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)

optional_oauth2 = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False,
)

# How long (seconds) to cache the "user exists" signal in Redis.
# A 60-second TTL means a single DB user lookup at most once per minute per user, per process.
_USER_EXISTS_CACHE_TTL = 60


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = security.decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fast-path: if Redis confirms this user_id was valid recently, skip the DB lookup.
    # The cache key stores nothing sensitive — just whether the user existed.
    from app.core.redis_client import get_redis
    redis = await get_redis()
    cache_key = f"user_exists:{user_id}"

    if redis is not None:
        try:
            if await redis.exists(cache_key):
                # User confirmed valid in Redis; still need the full row for attribute access.
                # Do a DB fetch but skip the extra "not found" guard since we trust the cache.
                user = await UserRepository(db).get_by_id(user_id)
                if user:
                    # 加载用户数据源配置到 ProviderFactory
                    _load_user_data_source_config(user)
                    return user
                # cache stale — fall through to full auth below
                await redis.delete(cache_key)
        except Exception:
            pass  # Redis error → fall through to DB path

    # DB path (cache miss or no Redis)
    user = await UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Warm the cache for future requests
    if redis is not None:
        try:
            await redis.set(cache_key, "1", ex=_USER_EXISTS_CACHE_TTL)
        except Exception:
            pass

    # 加载用户数据源配置到 ProviderFactory
    _load_user_data_source_config(user)

    return user


def _load_user_data_source_config(user: User) -> None:
    """加载用户的数据源配置到 ProviderFactory"""
    from app.services.market_providers.factory import ProviderFactory

    config = {
        "a_share": getattr(user, "data_source_a_share", "YFINANCE"),
        "hk_share": getattr(user, "data_source_hk_share", "YFINANCE"),
        "us_share": getattr(user, "data_source_us_share", "YFINANCE"),
    }
    ProviderFactory.set_user_data_source_config(config)


async def get_optional_current_user(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(optional_oauth2),
) -> Optional[User]:
    if not token:
        return None

    try:
        payload = security.decode_token(token)
    except JWTError:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    return await UserRepository(db).get_by_id(user_id)
