from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider_config import ProviderConfig


class ProviderConfigRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_key(self, provider_key: str):
        result = await self.db.execute(
            select(ProviderConfig).where(ProviderConfig.provider_key == provider_key)
        )
        return result.scalar_one_or_none()

    async def list_active(self):
        stmt = (
            select(ProviderConfig)
            .where(ProviderConfig.is_active == True)
            .order_by(ProviderConfig.priority.asc(), ProviderConfig.display_name.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def save(self, provider: ProviderConfig, refresh: bool = False):
        self.db.add(provider)
        try:
            await self.db.commit()
            if refresh:
                await self.db.refresh(provider)
            return provider
        except IntegrityError:
            await self.db.rollback()
            existing = await self.get_by_key(provider.provider_key)
            if existing is None:
                raise

            existing.display_name = provider.display_name
            existing.base_url = provider.base_url
            existing.api_key_env = provider.api_key_env
            existing.priority = provider.priority
            existing.is_active = provider.is_active
            existing.max_retries = provider.max_retries
            existing.timeout_seconds = provider.timeout_seconds
            await self.db.commit()
            if refresh:
                await self.db.refresh(existing)
            return existing
