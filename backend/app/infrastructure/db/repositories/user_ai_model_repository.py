from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_ai_model import UserAIModel


class UserAIModelRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_active_by_user(self, user_id: str):
        stmt = (
            select(UserAIModel)
            .where(UserAIModel.user_id == user_id, UserAIModel.is_active == True)
            .order_by(UserAIModel.updated_at.desc(), UserAIModel.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_key(self, user_id: str, key: str):
        stmt = select(UserAIModel).where(
            UserAIModel.user_id == user_id,
            UserAIModel.key == key,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def save(self, model: UserAIModel, refresh: bool = False):
        self.db.add(model)
        await self.db.commit()
        if refresh:
            await self.db.refresh(model)
        return model

    async def deactivate(self, model: UserAIModel, refresh: bool = False):
        model.is_active = False
        await self.db.commit()
        if refresh:
            await self.db.refresh(model)
        return model

    async def rollback(self):
        await self.db.rollback()
