"""
AI Service — 业务编排层
职责：模型配置解析、API Key 路由、故障转移分发、分析报告生成。
HTTP 传输逻辑已解耦至 app.services.ai_provider_client。
"""
# 设置代理环境变量（解决 Python 3.14 + httpx 兼容性问题）
import os
from app.core.config import settings
if settings.HTTP_PROXY:
    os.environ.setdefault("HTTP_PROXY", settings.HTTP_PROXY)
    os.environ.setdefault("HTTPS_PROXY", settings.HTTP_PROXY)
if settings.NO_PROXY:
    os.environ.setdefault("NO_PROXY", settings.NO_PROXY)
    os.environ.setdefault("no_proxy", settings.NO_PROXY)

from app.core import security
from app.core.prompts import build_stock_analysis_prompt, build_portfolio_analysis_prompt
from app.services.ai_provider_client import call_provider, infer_provider_key  # noqa: F401 (re-exported)
from app.core.redis_client import cache_get, cache_set
import logging
import httpx
import json
import time
import hashlib
from typing import Optional, List, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.ai_config import AIModelConfig
from app.models.provider_config import ProviderConfig
from app.models.user import User
from app.models.user_ai_model import UserAIModel
from app.models.user_provider_credential import UserProviderCredential
from app.schemas.ai_config import AIModelRuntimeConfig, ProviderRuntimeConfig


# 配置日志
logger = logging.getLogger(__name__)
# AI 调用专用 logger（与 ai_provider_client 共享同一 logger 名）
ai_call_logger = logging.getLogger("app.ai_calls")

class AIService:
    _model_config_cache = {}
    CACHE_TTL = 300  # 缓存 5 分钟
    _provider_cache = [] # 缓存供应商列表
    _provider_cache_time = 0
    # AI 响应缓存：{ prompt_hash: (response, timestamp) }
    _response_cache = {}
    RESPONSE_CACHE_TTL = 600  # 10 分钟

    @staticmethod
    def _hash_prompt(prompt: str) -> str:
        """生成 prompt 的 MD5 哈希值，用于缓存键"""
        return hashlib.md5(prompt.encode("utf-8")).hexdigest()

    @staticmethod
    def _format_exception(e: Exception) -> str:
        msg = str(e).strip()
        if msg:
            return msg
        return e.__class__.__name__

    @staticmethod
    def _normalize_user_model_base_url(raw_base_url: str | None) -> str:
        normalized = (raw_base_url or "").strip().rstrip("/")
        normalized = normalized.replace("/models", "").replace("/chat/completions", "")
        return normalized

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
    async def call_user_ai_model(cls, model: UserAIModel, prompt: str) -> str:
        if not model.encrypted_api_key:
            raise ValueError("User AI model missing API key")

        api_key = security.decrypt_api_key(model.encrypted_api_key)
        base_url = cls._normalize_user_model_base_url(model.base_url)
        provider_note = (model.provider_note or "").lower()
        is_gemini = "gemini" in provider_note or "googleapis.com" in base_url or "generativelanguage" in base_url

        provider_config = type(
            "TempProvider",
            (),
            {
                "provider_key": "gemini" if is_gemini else "custom",
                "base_url": base_url,
                "timeout_seconds": 300,
            },
        )()
        return await call_provider(provider_config, model.model_id, prompt, api_key, base_url)

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
                logger.warning(f"查询供应商 {provider_key} 默认模型失败：{e}")

        provider_defaults = {
            "siliconflow": "deepseek-ai/DeepSeek-V3",
            "deepseek": "deepseek-chat",
            "dashscope": "qwen3.5-plus",
        }
        return provider_defaults.get(provider_key, "gpt-4o-mini")

    @classmethod
    async def get_model_config(cls, model_key: str, db: AsyncSession = None) -> AIModelRuntimeConfig:
        """获取模型配置的阶梯式查找，返回解耦的 Pydantic 模型"""
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
                    # 立即转换为字典保存到缓存，避免 Session 关闭后无法访问
                    config_data = {
                        "key": config.key,
                        "provider": config.provider,
                        "model_id": config.model_id,
                        "description": config.description
                    }
                    cls._model_config_cache[model_key] = (config_data, time.time())
                    return AIModelRuntimeConfig(**config_data)
            except Exception as e:
                logger.error(f"查询 AI 模型配置失败：{e}")

        # 兜底回退
        fallback_map = {
            "deepseek-v3": "Pro/deepseek-ai/DeepSeek-V3",
            "deepseek-r1": "Pro/deepseek-ai/DeepSeek-R1",
            "qwen-3-vl-thinking": "Qwen/Qwen3-VL-235B-A22B-Thinking",
        }
        fallback_id = fallback_map.get(model_key, "Pro/deepseek-ai/DeepSeek-V3")
        provider = "dashscope" if ("qwen" in model_key or "dashscope" in model_key) else "siliconflow"
        return AIModelRuntimeConfig(key=model_key, provider=provider, model_id=fallback_id)

    @staticmethod
    async def _resolve_api_key(
        provider_key: str,
        user: Optional[User],
        db: Optional[AsyncSession] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        统一 API Key & URL 解析器：优先级 用户级加密 Key > 系统级 Key
        返回：(api_key, custom_base_url)
        """
        custom_base_url = None

        if user:
            # 0. 优先从统一凭据表中读取
            if db:
                try:
                    credential_stmt = select(UserProviderCredential).where(
                        UserProviderCredential.user_id == user.id,
                        UserProviderCredential.provider_key == provider_key,
                        UserProviderCredential.is_enabled == True,
                    )
                    credential_result = await db.execute(credential_stmt)
                    credential = credential_result.scalar_one_or_none()
                    if credential:
                        decrypted_key = None
                        if credential.encrypted_api_key:
                            try:
                                decrypted_key = security.decrypt_api_key(credential.encrypted_api_key)
                            except Exception as e:
                                logger.error(f"解密用户 {provider_key} 统一凭据失败：{e}")
                        if decrypted_key or credential.base_url:
                            return decrypted_key, credential.base_url
                except Exception as e:
                    logger.warning(f"查询用户 {user.id} 的统一 Provider 凭据失败：{e}")

            # 1. 尝试从 api_configs JSON 中解析自定义配置
            if user.api_configs:
                try:
                    configs = json.loads(user.api_configs)
                    if provider_key in configs:
                        custom_base_url = configs[provider_key].get("base_url")
                except Exception as e:
                    logger.warning(f"解析用户 {user.id} 的 api_configs 失败：{e}")

            # 2. 从用户表获取加密的 Key
            user_key_attr = f"api_key_{provider_key}"
            if hasattr(user, user_key_attr):
                encrypted_key = getattr(user, user_key_attr)
                if encrypted_key:
                    try:
                        return security.decrypt_api_key(encrypted_key), custom_base_url
                    except Exception as e:
                        logger.error(f"解密用户 {provider_key} API Key 失败：{e}")

        # 3. 降级到系统环境变量
        env_key_map = {
            "siliconflow": settings.SILICONFLOW_API_KEY,
            "deepseek": settings.DEEPSEEK_API_KEY,
            "dashscope": settings.DASHSCOPE_API_KEY,
            "gemini": settings.GEMINI_API_KEY,
        }
        return env_key_map.get(provider_key), None

    @staticmethod
    async def call_provider(
        provider_config: Any,
        model_id: str,
        prompt: str,
        api_key: str,
        custom_url: str = None,
        require_json: bool = True,
    ) -> str:
        """通用供应商调用器 — 委托至 ai_provider_client.call_provider"""
        return await call_provider(provider_config, model_id, prompt, api_key, custom_url, require_json)

    @classmethod
    @classmethod
    async def call_siliconflow(
        cls,
        prompt: str,
        api_key: str,
        model: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        base_url: Optional[str] = None,
    ) -> str:
        """
        [已废弃] SiliconFlow 专用快捷入口。
        请改用 AIService.generate_text(prompt, db) —— 它会自动按 DB 配置的 provider 优先级路由，支持故障转移。
        """
        target_model = model
        if not target_model:
            # 避免 DEFAULT_AI_MODEL 指向其他供应商（如 dashscope）导致向 siliconflow 发送不存在的模型 ID
            target_model = await cls.get_default_model_for_provider("siliconflow", db)

        model_config = await cls.get_model_config(target_model, db)
        if model_config.provider != "siliconflow":
            model_id = await cls.get_default_model_for_provider("siliconflow", db)
        else:
            model_id = model_config.model_id

        provider_config = ProviderRuntimeConfig(
            provider_key="siliconflow",
            base_url=base_url or "https://api.siliconflow.cn/v1",
            timeout_seconds=300,
        )
        return await cls.call_provider(
            provider_config,
            model_id,
            prompt,
            api_key,
            base_url,
        )

    @classmethod
    async def test_connection(
        cls,
        provider_key: str,
        api_key: str,
        base_url: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        model_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """测试 AI 供应商连接性"""
        try:
            # 构造临时供应商配置对象
            default_url = base_url or ""
            if not default_url and db:
                try:
                    stmt = select(ProviderConfig).where(ProviderConfig.provider_key == provider_key)
                    result = await db.execute(stmt)
                    provider = result.scalar_one_or_none()
                    if provider:
                        default_url = provider.base_url
                except Exception as e:
                    logger.warning(f"查询供应商 {provider_key} 默认地址失败：{e}")

            if not default_url:
                default_url = "https://api.siliconflow.cn/v1" if provider_key == "siliconflow" else ""

            provider_config = ProviderRuntimeConfig(
                provider_key=provider_key,
                base_url=default_url,
                timeout_seconds=60  # thinking 模型冷启动可能需要 30s+
            )

            test_prompt = "Say ok"
            # 根据供应商选择一个轻量模型进行测试
            test_model = model_id or await cls.get_default_model_for_provider(provider_key, db)

            print(f"\n[AI_DEBUG] 开始测试连接：{provider_key}")
            await cls.call_provider(provider_config, test_model, test_prompt, api_key, base_url, require_json=False)
            print(f"[AI_DEBUG] 测试连接成功")
            return True, "连接成功"
        except httpx.ReadTimeout:
            logger.warning(f"AI 供应商 {provider_key} 连接测试超时")
            return False, "连接失败：请求超时，供应商无响应（thinking 模型首次响应可能需要更长时间）"
        except Exception as e:
            error_msg = str(e) or e.__class__.__name__
            logger.warning(f"AI 供应商 {provider_key} 连接测试失败：{error_msg}")
            return False, f"连接失败：{error_msg}"

    @staticmethod
    def infer_provider_key(base_url: Optional[str] = None, provider_hint: Optional[str] = None) -> str:
        """委托至 ai_provider_client.infer_provider_key"""
        return infer_provider_key(base_url, provider_hint)

    @classmethod
    async def _dispatch_with_fallback(cls, prompt: str, model_config: AIModelRuntimeConfig, user: Optional[User], db: AsyncSession) -> str:
        """核心路由：带故障转移的提供商分发"""

        # 1. 获取所有可用的供应商列表，按优先级排序
        # 注意：缓存时提取属性值，避免 ORM 对象在 session 关闭后无法访问
        try:
            if time.time() - cls._provider_cache_time > 600 or not cls._provider_cache:
                stmt = select(ProviderConfig).where(ProviderConfig.is_active == True).order_by(ProviderConfig.priority.asc())
                result = await db.execute(stmt)
                raw_providers = result.scalars().all()
                # 提取关键属性，避免 ORM 对象在 session 关闭后失效
                cls._provider_cache = [
                    {
                        'provider_key': p.provider_key,
                        'base_url': p.base_url,
                        'timeout_seconds': p.timeout_seconds or 120,
                    }
                    for p in raw_providers
                ]
                cls._provider_cache_time = time.time()
        except Exception as e:
            logger.warning(f"获取供应商配置失败：{e}，使用内存缓存的供应商列表")
            if not cls._provider_cache:
                return f"**Error**: AI 服务暂时不可用 (无法获取供应商配置：{e})"

        if not cls._provider_cache:
            return f"**Error**: AI 服务暂时不可用 (没有可用的 AI 供应商)"

        preferred_key = model_config.provider
        ordered_providers = sorted(
            cls._provider_cache,
            key=lambda p: (0 if p["provider_key"] == preferred_key else 1),
        )
        provider_errors: List[str] = []
        attempted = 0

        for provider in ordered_providers:
            provider_key = provider["provider_key"]
            try:
                api_key, custom_url = await cls._resolve_api_key(provider_key, user, db)
                if not api_key:
                    provider_errors.append(f"{provider_key}: 缺少 API Key")
                    continue

                current_model_id = (
                    model_config.model_id
                    if provider_key == preferred_key
                    else await cls.get_default_model_for_provider(provider_key, db)
                )
                logger.info(f"使用供应商 {provider_key} (Model: {current_model_id}) URL: {custom_url or 'default'}")

                provider_config = ProviderRuntimeConfig(
                    provider_key=provider_key,
                    base_url=custom_url or provider["base_url"],
                    timeout_seconds=provider.get("timeout_seconds", 120),
                )
                attempted += 1
                return await cls.call_provider(provider_config, current_model_id, prompt, api_key, custom_url)
            except Exception as e:
                err = cls._format_exception(e)
                provider_errors.append(f"{provider_key}: {err}")
                logger.error(f"供应商 {provider_key} 调用失败：{err}")
                continue

        if attempted == 0:
            return f"**Error**: AI 服务暂时不可用 (没有可用的供应商凭据)。详情：{' | '.join(provider_errors[:3])}"

        last_error = provider_errors[-1] if provider_errors else "unknown"
        return f"**Error**: AI 服务暂时不可用 (尝试了 {attempted} 个供应商)。最后错误：{last_error}"

    @classmethod
    async def generate_analysis(cls, ticker: str, market_data: dict, news_data: list = None,
                                macro_context: str = None, fundamental_data: dict = None, previous_analysis: dict = None,
                                model: Optional[str] = None, db: AsyncSession = None, user_id: str = None,
                                fomc_days_away: int = None, next_fomc_date: str = None,
                                earnings_date: str = None, vix_level: float = None,
                                analyst_summary: str = None,
                                pre_computed_news: str = None,
                                pre_computed_fundamental: str = None) -> str:
        """主方法：生成个股深度诊断（带缓存）"""
        model_key = model or settings.DEFAULT_AI_MODEL

        user = None
        if user_id and db:
            try:
                user_stmt = select(User).where(User.id == user_id)
                user_result = await db.execute(user_stmt)
                user = user_result.scalar_one_or_none()
            except Exception as e:
                logger.warning(f"获取用户信息失败：{e}")

        prompt = build_stock_analysis_prompt(
            ticker=ticker,
            market_data=market_data,
            fundamental_data=fundamental_data or {},
            news_data=news_data or [],
            macro_context=macro_context,
            previous_analysis=previous_analysis,
            fomc_days_away=fomc_days_away,
            next_fomc_date=next_fomc_date,
            earnings_date=earnings_date,
            vix_level=vix_level,
            analyst_summary=analyst_summary,
            pre_computed_news=pre_computed_news,
            pre_computed_fundamental=pre_computed_fundamental,
        )

        # 1. 检查内存缓存 (相同 prompt 直接返回)
        prompt_hash = cls._hash_prompt(prompt)
        if prompt_hash in cls._response_cache:
            cached_response, cached_time = cls._response_cache[prompt_hash]
            if time.time() - cached_time < cls.RESPONSE_CACHE_TTL:
                logger.info(f"[AI Cache] HIT (memory) for {ticker}")
                return cached_response

        # 2. 检查 Redis 缓存
        redis_cache_key = f"ai:analysis:{prompt_hash}"
        cached = await cache_get(redis_cache_key)
        if cached:
            logger.info(f"[AI Cache] HIT (redis) for {ticker}")
            cls._response_cache[prompt_hash] = (cached, time.time())
            return cached

        if user and db:
            user_model = await cls.get_user_ai_model(model_key, user.id, db)
            if user_model:
                try:
                    result = await cls.call_user_ai_model(user_model, prompt)
                    # 缓存结果
                    cls._response_cache[prompt_hash] = (result, time.time())
                    await cache_set(redis_cache_key, result, ttl_seconds=cls.RESPONSE_CACHE_TTL)
                    return result
                except Exception as e:
                    logger.warning(f"用户自定义模型 {model_key} 调用失败：{e}")
                    if not user:
                        return f"**Error**: AI 调用失败。错误：{e}"
                    return f"**Error**: 用户自定义模型 {model_key} 调用失败。错误：{e}"

        model_config = await cls.get_model_config(model_key, db)
        result = await cls._dispatch_with_fallback(prompt, model_config, user, db)

        # 缓存结果 (错误信息短暂缓存)
        if not result.startswith("**Error**"):
            cls._response_cache[prompt_hash] = (result, time.time())
            await cache_set(redis_cache_key, result, ttl_seconds=cls.RESPONSE_CACHE_TTL)
        else:
            await cache_set(redis_cache_key, result, ttl_seconds=60)

        return result

    @classmethod
    async def generate_portfolio_analysis(cls, portfolio_items: list, market_news: str = None, macro_context: str = None,
                                          model: Optional[str] = None, db: AsyncSession = None, user_id: str = None) -> str:
        """生成全量持仓健康诊断报告（带缓存）"""
        if not portfolio_items:
            return json.dumps({"error": "暂无持仓数据"})
        model_key = model or settings.DEFAULT_AI_MODEL

        user = None
        if user_id and db:
            user_stmt = select(User).where(User.id == user_id)
            user_result = await db.execute(user_stmt)
            user = user_result.scalar_one_or_none()

        # Format holdings list into a readable string for the prompt
        holdings_text = "\n".join(
            f"- {h.get('ticker', '?')} ({h.get('name', '')}): "
            f"市值=${h.get('market_value', 0):.2f}, "
            f"盈亏={h.get('pl_percent', 0):.2f}%, "
            f"行业={h.get('sector', '未知')}, "
            f"RRR={h.get('rrr') if h.get('rrr') is not None else 'N/A'}"
            for h in portfolio_items
        )
        # Note: build_portfolio_analysis_prompt signature is (holdings_context, macro_context, market_news)
        prompt = build_portfolio_analysis_prompt(holdings_text, macro_context, market_news)

        # 检查缓存
        prompt_hash = cls._hash_prompt(prompt)
        if prompt_hash in cls._response_cache:
            cached_response, cached_time = cls._response_cache[prompt_hash]
            if time.time() - cached_time < cls.RESPONSE_CACHE_TTL:
                logger.info(f"[AI Cache] HIT (memory) for portfolio analysis")
                return cached_response

        redis_cache_key = f"ai:portfolio:{prompt_hash}"
        cached = await cache_get(redis_cache_key)
        if cached:
            logger.info(f"[AI Cache] HIT (redis) for portfolio analysis")
            cls._response_cache[prompt_hash] = (cached, time.time())
            return cached

        if user and db:
            user_model = await cls.get_user_ai_model(model_key, user.id, db)
            if user_model:
                try:
                    result = await cls.call_user_ai_model(user_model, prompt)
                    cls._response_cache[prompt_hash] = (result, time.time())
                    await cache_set(redis_cache_key, result, ttl_seconds=cls.RESPONSE_CACHE_TTL)
                    return result
                except Exception as e:
                    logger.warning(f"用户自定义组合模型 {model_key} 调用失败：{e}")
                    return json.dumps({"error": f"AI 服务暂时不可用：{e}"})

        model_config = await cls.get_model_config(model_key, db)
        result = await cls._dispatch_with_fallback(prompt, model_config, user, db)

        # 缓存结果
        if not result.startswith("**Error**") and not result.startswith('{"error"'):
            cls._response_cache[prompt_hash] = (result, time.time())
            await cache_set(redis_cache_key, result, ttl_seconds=cls.RESPONSE_CACHE_TTL)

        return result

    @classmethod
    async def generate_text(
        cls,
        prompt: str,
        db: AsyncSession,
        model_key: Optional[str] = None,
    ) -> str:
        """
        系统级通用文本生成入口（无用户上下文）。

        适用于后台任务、定时任务、数据流水线等不依赖特定用户 AI 配置的场景。
        自动按数据库中的 provider 优先级路由，支持故障转移。

        Args:
            prompt:     发送给 LLM 的完整 Prompt 字符串。
            db:         AsyncSession，用于查询 provider 配置。
            model_key:  模型 key（如 "qwen3.5-plus"），默认使用 settings.DEFAULT_AI_MODEL。

        Returns:
            LLM 返回的文本。失败时返回以 "**Error**" 开头的错误描述。
        """
        key = model_key or settings.DEFAULT_AI_MODEL
        model_config = await cls.get_model_config(key, db)
        return await cls._dispatch_with_fallback(prompt, model_config, user=None, db=db)


ai_service = AIService
