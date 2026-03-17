from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.db.repositories.ai_model_repository import AIModelRepository
from app.infrastructure.db.repositories.provider_config_repository import ProviderConfigRepository
from app.models.ai_config import AIModelConfig
from app.models.provider_config import ProviderConfig

PUBLIC_SYSTEM_MODEL_KEYS = {"qwen3.5-plus"}


async def ensure_system_ai_registry(db: AsyncSession) -> None:
    provider_repo = ProviderConfigRepository(db)
    model_repo = AIModelRepository(db)

    provider = await provider_repo.get_by_key("dashscope")
    if provider is None:
        provider = ProviderConfig(
            provider_key="dashscope",
            display_name="DashScope",
            base_url=(settings.DASHSCOPE_BASE_URL or "https://coding.dashscope.aliyuncs.com/v1").rstrip("/"),
            api_key_env="DASHSCOPE_API_KEY",
            priority=20,
            is_active=True,
            max_retries=3,
            timeout_seconds=60,
        )
    else:
        provider.display_name = "DashScope"
        provider.base_url = (settings.DASHSCOPE_BASE_URL or provider.base_url).rstrip("/")
        provider.api_key_env = "DASHSCOPE_API_KEY"
        provider.is_active = True
        provider.priority = provider.priority or 20
        provider.timeout_seconds = provider.timeout_seconds or 60

    await provider_repo.save(provider)

    model = await model_repo.get_by_key("qwen3.5-plus")
    if model is None:
        model = AIModelConfig(
            key="qwen3.5-plus",
            provider="dashscope",
            model_id="qwen3.5-plus",
            is_active=True,
            description="[builtin-public] 通义千问 Plus（系统内置）",
        )
    else:
        model.provider = "dashscope"
        model.model_id = "qwen3.5-plus"
        model.is_active = True
        model.description = "[builtin-public] 通义千问 Plus（系统内置）"

    await model_repo.save(model)
