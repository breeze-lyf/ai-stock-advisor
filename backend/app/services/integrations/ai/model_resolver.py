"""
Model Resolver — configuration lookup, API key resolution, caching.
Handles: model config DB queries, user credential decryption, provider defaults.
"""
import json
import logging
import time
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core import security
from app.core.config import settings
from app.models.ai_config import AIModelConfig
from app.models.provider_config import ProviderConfig
from app.models.user import User
from app.models.user_ai_model import UserAIModel
from app.models.user_provider_credential import UserProviderCredential
from app.schemas.ai_config import AIModelRuntimeConfig

logger = logging.getLogger(__name__)


class ModelResolver:
    _model_config_cache = {}
    CACHE_TTL = 300
    _provider_cache = []
    _provider_cache_time = 0

    @classmethod
    async def get_user_ai_model(
        cls,
        model_key: str,
        user_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[UserAIModel]:
        if not db:
            return None
        stmt = select(UserAIModel).where(
            UserAIModel.user_id == user_id,
            UserAIModel.key == model_key,
            UserAIModel.is_active == True,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_default_model_for_provider(cls, provider_key: str, db: Optional[AsyncSession] = None) -> str:
        if db:
            try:
                stmt = (
                    select(AIModelConfig)
                    .where(AIModelConfig.provider == provider_key, AIModelConfig.is_active == True)
                    .order_by(AIModelConfig.updated_at.desc(), AIModelConfig.created_at.desc())
                    .limit(1)
                )
                result = await db.execute(stmt)
                config = result.scalar_one_or_none()
                if config:
                    return config.model_id
            except Exception as e:
                logger.warning(f"Query default model for provider {provider_key} failed: {e}")

        provider_defaults = {
            "siliconflow": "deepseek-ai/DeepSeek-V3",
            "deepseek": "deepseek-chat",
            "dashscope": "qwen3.5-plus",
        }
        return provider_defaults.get(provider_key, "gpt-4o-mini")

    @classmethod
    async def get_model_config(cls, model_key: str, db: AsyncSession = None) -> AIModelRuntimeConfig:
        """阶梯式模型配置查找：缓存 → DB → 兜底回退。"""
        if model_key in cls._model_config_cache:
            config_data, timestamp = cls._model_config_cache[model_key]
            if time.time() - timestamp < cls.CACHE_TTL:
                return AIModelRuntimeConfig(**config_data)

        if db:
            try:
                stmt = select(AIModelConfig).where(AIModelConfig.key == model_key)
                result = await db.execute(stmt)
                config = result.scalar_one_or_none()
                if config:
                    config_data = {
                        "key": config.key,
                        "provider": config.provider,
                        "model_id": config.model_id,
                        "description": config.description,
                    }
                    cls._model_config_cache[model_key] = (config_data, time.time())
                    return AIModelRuntimeConfig(**config_data)
            except Exception as e:
                logger.error(f"Query AI model config failed: {e}")

        fallback_map = {
            "deepseek-v4-flash": "deepseek-v4-flash",
            "deepseek-v3": "Pro/deepseek-ai/DeepSeek-V3",
            "deepseek-r1": "Pro/deepseek-ai/DeepSeek-R1",
            "qwen-3-vl-thinking": "Qwen/Qwen3-VL-235B-A22B-Thinking",
        }
        fallback_id = fallback_map.get(model_key, "Pro/deepseek-ai/DeepSeek-V3")
        if "qwen" in model_key or "dashscope" in model_key:
            provider = "dashscope"
        elif model_key.startswith("deepseek-v4") or model_key == "deepseek-chat":
            provider = "deepseek"
        else:
            provider = "siliconflow"
        return AIModelRuntimeConfig(key=model_key, provider=provider, model_id=fallback_id)

    @classmethod
    async def get_provider_list(cls, db: AsyncSession) -> list[dict]:
        """获取排序后的供应商列表（带缓存）。"""
        if time.time() - cls._provider_cache_time > 600 or not cls._provider_cache:
            try:
                stmt = select(ProviderConfig).where(ProviderConfig.is_active == True).order_by(ProviderConfig.priority.asc())
                result = await db.execute(stmt)
                raw_providers = result.scalars().all()
                cls._provider_cache = [
                    {
                        "provider_key": p.provider_key,
                        "base_url": p.base_url,
                        "timeout_seconds": p.timeout_seconds or 120,
                    }
                    for p in raw_providers
                ]
                cls._provider_cache_time = time.time()
            except Exception as e:
                logger.warning(f"Failed to fetch provider configs: {e}")
                if not cls._provider_cache:
                    raise RuntimeError(f"Cannot get provider config: {e}") from e
        return cls._provider_cache

    @staticmethod
    async def resolve_api_key(
        provider_key: str,
        user: Optional[User],
        db: Optional[AsyncSession] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        统一 API Key 解析：优先级 用户统一凭据 > api_configs JSON > 用户表字段 > 系统环境变量。
        返回：(api_key, custom_base_url)
        """
        custom_base_url = None

        if user:
            # 1. 统一凭据表
            if db:
                try:
                    stmt = select(UserProviderCredential).where(
                        UserProviderCredential.user_id == user.id,
                        UserProviderCredential.provider_key == provider_key,
                        UserProviderCredential.is_enabled == True,
                    )
                    result = await db.execute(stmt)
                    cred = result.scalar_one_or_none()
                    if cred:
                        decrypted = None
                        if cred.encrypted_api_key:
                            try:
                                decrypted = security.decrypt_api_key(cred.encrypted_api_key)
                            except Exception as e:
                                logger.error(f"Decrypt credential for {provider_key} failed: {e}")
                        if decrypted or cred.base_url:
                            return decrypted, cred.base_url
                except Exception as e:
                    logger.warning(f"Query user provider credential for {user.id} failed: {e}")

            # 2. api_configs JSON
            if user.api_configs:
                try:
                    configs = json.loads(user.api_configs)
                    if provider_key in configs:
                        custom_base_url = configs[provider_key].get("base_url")
                except Exception as e:
                    logger.warning(f"Parse api_configs for {user.id} failed: {e}")

            # 3. 用户表字段
            user_key_attr = f"api_key_{provider_key}"
            if hasattr(user, user_key_attr):
                encrypted_key = getattr(user, user_key_attr)
                if encrypted_key:
                    try:
                        return security.decrypt_api_key(encrypted_key), custom_base_url
                    except Exception as e:
                        logger.error(f"Decrypt user API key for {provider_key} failed: {e}")

        # 4. 系统环境变量
        env_map = {
            "siliconflow": settings.SILICONFLOW_API_KEY,
            "deepseek": settings.DEEPSEEK_API_KEY,
            "dashscope": settings.DASHSCOPE_API_KEY,
            "gemini": settings.GEMINI_API_KEY,
        }
        return env_map.get(provider_key), None

    @staticmethod
    def normalize_user_model_base_url(raw_base_url: str | None) -> str:
        normalized = (raw_base_url or "").strip().rstrip("/")
        normalized = normalized.replace("/models", "").replace("/chat/completions", "")
        return normalized
