from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_config import AIModelConfig


class AIModelRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_active(self):
        stmt = (
            select(AIModelConfig)
            .where(AIModelConfig.is_active == True)
            .order_by(AIModelConfig.provider.asc(), AIModelConfig.key.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_key(self, key: str):
        result = await self.db.execute(select(AIModelConfig).where(AIModelConfig.key == key))
        return result.scalar_one_or_none()

    async def save(self, config: AIModelConfig):
        self.db.add(config)
        try:
            await self.db.commit()
            await self.db.refresh(config)
            return config
        except IntegrityError:
            await self.db.rollback()
            existing = await self.get_by_key(config.key)
            if existing is None:
                raise

            existing.provider = config.provider
            existing.model_id = config.model_id
            existing.is_active = config.is_active
            existing.description = config.description
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

    async def deactivate(self, config: AIModelConfig):
        config.is_active = False
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def rollback(self):
        await self.db.rollback()
