from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_provider_credential import UserProviderCredential


class UserProviderCredentialRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_user_id(self, user_id: str):
        stmt = (
            select(UserProviderCredential)
            .where(UserProviderCredential.user_id == user_id)
            .order_by(UserProviderCredential.provider_key.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_user_and_provider(self, user_id: str, provider_key: str):
        stmt = select(UserProviderCredential).where(
            UserProviderCredential.user_id == user_id,
            UserProviderCredential.provider_key == provider_key,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: str,
        provider_key: str,
        encrypted_api_key: str | None = None,
        base_url: str | None = None,
        is_enabled: bool | None = None,
    ):
        credential = await self.get_by_user_and_provider(user_id, provider_key)
        if credential is None:
            credential = UserProviderCredential(
                user_id=user_id,
                provider_key=provider_key,
            )
            self.db.add(credential)

        if encrypted_api_key is not None:
            credential.encrypted_api_key = encrypted_api_key
        if base_url is not None:
            credential.base_url = base_url
        if is_enabled is not None:
            credential.is_enabled = is_enabled

        return credential

    async def commit(self):
        await self.db.commit()

    async def rollback(self):
        await self.db.rollback()
