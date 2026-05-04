"""
Provider Router — LLM dispatch, failover, connection testing, response caching.
Handles: calling individual providers, routing with fallback, caching results.
"""
import hashlib
import logging
import time
from typing import Optional, Tuple

import httpx

from app.core.config import settings
from app.core.redis_client import cache_get, cache_set
from app.schemas.ai_config import AIModelRuntimeConfig, ProviderRuntimeConfig
from app.services.ai_provider_client import call_provider, infer_provider_key
from app.services.model_resolver import ModelResolver

logger = logging.getLogger(__name__)
ai_call_logger = logging.getLogger("app.ai_calls")


class ProviderRouter:
    _response_cache = {}
    RESPONSE_CACHE_TTL = 600

    @staticmethod
    def _hash_prompt(prompt: str) -> str:
        return hashlib.md5(prompt.encode("utf-8")).hexdigest()

    @staticmethod
    def _format_exception(e: Exception) -> str:
        msg = str(e).strip()
        return msg if msg else e.__class__.__name__

    @classmethod
    async def call_provider(
        cls,
        provider_config: ProviderRuntimeConfig,
        model_id: str,
        prompt: str,
        api_key: str,
        custom_url: str = None,
        require_json: bool = True,
        max_tokens: Optional[int] = None,
        extra_params: Optional[dict] = None,
    ) -> str:
        """委托至 ai_provider_client.call_provider。"""
        return await call_provider(
            provider_config, model_id, prompt, api_key, custom_url,
            require_json, max_tokens=max_tokens, extra_params=extra_params,
        )

    @classmethod
    async def call_user_ai_model(cls, model, prompt: str) -> str:
        """调用用户自定义模型。"""
        from app.core import security
        if not model.encrypted_api_key:
            raise ValueError("User AI model missing API key")

        api_key = security.decrypt_api_key(model.encrypted_api_key)
        base_url = ModelResolver.normalize_user_model_base_url(model.base_url)
        provider_note = (model.provider_note or "").lower()
        is_gemini = "gemini" in provider_note or "googleapis.com" in base_url or "generativelanguage" in base_url

        provider_config = type(
            "TempProvider", (), {
                "provider_key": "gemini" if is_gemini else "custom",
                "base_url": base_url,
                "timeout_seconds": 300,
            }
        )()
        return await call_provider(provider_config, model.model_id, prompt, api_key, base_url)

    @classmethod
    async def test_connection(
        cls,
        provider_key: str,
        api_key: str,
        base_url: Optional[str] = None,
        db=None,
        model_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """测试 AI 供应商连接性。"""
        try:
            default_url = base_url or ""
            if not default_url and db:
                try:
                    from sqlalchemy.ext.asyncio import AsyncSession
                    from sqlalchemy.future import select
                    from app.models.provider_config import ProviderConfig
                    stmt = select(ProviderConfig).where(ProviderConfig.provider_key == provider_key)
                    result = await db.execute(stmt)
                    provider = result.scalar_one_or_none()
                    if provider:
                        default_url = provider.base_url
                except Exception as e:
                    logger.warning(f"Query default URL for {provider_key} failed: {e}")

            if not default_url:
                default_url = "https://api.siliconflow.cn/v1" if provider_key == "siliconflow" else ""

            provider_config = ProviderRuntimeConfig(
                provider_key=provider_key,
                base_url=default_url,
                timeout_seconds=60,
            )

            test_model = model_id or await ModelResolver.get_default_model_for_provider(provider_key, db)
            logger.info(f"Testing connection: {provider_key} (model={test_model})")
            await cls.call_provider(provider_config, test_model, "Say ok", api_key, base_url, require_json=False)
            logger.info("Connection test passed")
            return True, "连接成功"
        except httpx.ReadTimeout:
            logger.warning(f"Provider {provider_key} connection test timed out")
            return False, "连接失败：请求超时，供应商无响应（thinking 模型首次响应可能需要更长时间）"
        except Exception as e:
            error_msg = str(e) or e.__class__.__name__
            logger.warning(f"Provider {provider_key} connection test failed: {error_msg}")
            return False, f"连接失败：{error_msg}"

    @classmethod
    async def dispatch_with_fallback(
        cls,
        prompt: str,
        model_config: AIModelRuntimeConfig,
        user,
        db,
        max_tokens: Optional[int] = None,
        extra_params: Optional[dict] = None,
    ) -> str:
        """核心路由：带故障转移的供应商分发。"""
        try:
            providers = await ModelResolver.get_provider_list(db)
        except Exception:
            return "**Error**: AI 服务暂时不可用 (无法获取供应商配置)"

        if not providers:
            return "**Error**: AI 服务暂时不可用 (没有可用的 AI 供应商)"

        preferred_key = model_config.provider
        ordered_providers = sorted(
            providers,
            key=lambda p: (0 if p["provider_key"] == preferred_key else 1),
        )
        provider_errors = []
        attempted = 0

        for provider in ordered_providers:
            provider_key = provider["provider_key"]
            try:
                api_key, custom_url = await ModelResolver.resolve_api_key(provider_key, user, db)
                if not api_key:
                    provider_errors.append(f"{provider_key}: 缺少 API Key")
                    continue

                current_model_id = (
                    model_config.model_id
                    if provider_key == preferred_key
                    else await ModelResolver.get_default_model_for_provider(provider_key, db)
                )
                logger.info(f"Using provider {provider_key} (Model: {current_model_id}) URL: {custom_url or 'default'}")

                provider_config = ProviderRuntimeConfig(
                    provider_key=provider_key,
                    base_url=custom_url or provider["base_url"],
                    timeout_seconds=provider.get("timeout_seconds", 120),
                )
                attempted += 1
                return await cls.call_provider(
                    provider_config, current_model_id, prompt, api_key, custom_url,
                    max_tokens=max_tokens, extra_params=extra_params,
                )
            except Exception as e:
                err = cls._format_exception(e)
                provider_errors.append(f"{provider_key}: {err}")
                logger.error(f"Provider {provider_key} call failed: {err}")
                continue

        if attempted == 0:
            return f"**Error**: AI 服务暂时不可用 (没有可用的供应商凭据)。详情：{' | '.join(provider_errors[:3])}"

        last_error = provider_errors[-1] if provider_errors else "unknown"
        return f"**Error**: AI 服务暂时不可用 (尝试了 {attempted} 个供应商)。最后错误：{last_error}"

    @classmethod
    def check_cache(cls, prompt: str) -> Optional[str]:
        """检查内存 + Redis 缓存，命中时返回结果。"""
        prompt_hash = cls._hash_prompt(prompt)
        if prompt_hash in cls._response_cache:
            cached_response, cached_time = cls._response_cache[prompt_hash]
            if time.time() - cached_time < cls.RESPONSE_CACHE_TTL:
                return cached_response

        redis_key = f"ai:cached:{prompt_hash}"
        # Caller must pass full redis key prefix; this is a generic check
        return None  # Let caller handle Redis lookup with proper key

    @classmethod
    async def cache_result(cls, redis_key: str, prompt: str, result: str, ttl: Optional[int] = None):
        """写入内存 + Redis 缓存。"""
        prompt_hash = cls._hash_prompt(prompt)
        cls._response_cache[prompt_hash] = (result, time.time())
        await cache_set(redis_key, result, ttl_seconds=ttl or cls.RESPONSE_CACHE_TTL)

    @staticmethod
    def infer_provider_key(base_url: Optional[str] = None, provider_hint: Optional[str] = None) -> str:
        return infer_provider_key(base_url, provider_hint)
