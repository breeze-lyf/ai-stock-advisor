"""
AI Service — 业务编排层
职责：组装 Prompt → 调用 Provider Router → 缓存结果。
模型配置解析 → model_resolver.py
供应商分发/故障转移 → provider_router.py
"""
import os
from app.core.config import settings
if settings.HTTP_PROXY:
    os.environ.setdefault("HTTP_PROXY", settings.HTTP_PROXY)
    os.environ.setdefault("HTTPS_PROXY", settings.HTTP_PROXY)
if settings.NO_PROXY:
    os.environ.setdefault("NO_PROXY", settings.NO_PROXY)
    os.environ.setdefault("no_proxy", settings.NO_PROXY)

import json
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.prompts import build_stock_analysis_prompt, build_portfolio_analysis_prompt
from app.core.redis_client import cache_get, cache_set
from app.models.user import User
from app.schemas.ai_config import AIModelRuntimeConfig
from app.services.model_resolver import ModelResolver
from app.services.provider_router import ProviderRouter

logger = logging.getLogger(__name__)


class AIService:
    """AI 分析服务 — 纯编排，不包含底层 provider 调用细节。"""

    @classmethod
    async def generate_analysis(
        cls,
        ticker: str,
        market_data: dict,
        news_data: list = None,
        macro_context: str = None,
        fundamental_data: dict = None,
        previous_analysis: dict = None,
        model: Optional[str] = None,
        db: AsyncSession = None,
        user_id: str = None,
        fomc_days_away: int = None,
        next_fomc_date: str = None,
        earnings_date: str = None,
        vix_level: float = None,
        analyst_summary: str = None,
        pre_computed_news: str = None,
        pre_computed_fundamental: str = None,
    ) -> str:
        """主方法：生成个股深度诊断（带缓存）。"""
        model_key = model or settings.DEFAULT_AI_MODEL

        user = None
        if user_id and db:
            try:
                user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
            except Exception as e:
                logger.warning(f"Failed to get user info: {e}")

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

        prompt_hash = ProviderRouter._hash_prompt(prompt)
        redis_cache_key = f"ai:analysis:{prompt_hash}"

        # 检查内存缓存
        if prompt_hash in ProviderRouter._response_cache:
            cached_response, cached_time = ProviderRouter._response_cache[prompt_hash]
            import time
            if time.time() - cached_time < ProviderRouter.RESPONSE_CACHE_TTL:
                logger.info(f"[AI Cache] HIT (memory) for {ticker}")
                return cached_response

        # 检查 Redis 缓存
        cached = await cache_get(redis_cache_key)
        if cached:
            logger.info(f"[AI Cache] HIT (redis) for {ticker}")
            ProviderRouter._response_cache[prompt_hash] = (cached, __import__("time").time())
            return cached

        # 用户自定义模型优先
        if user and db:
            user_model = await ModelResolver.get_user_ai_model(model_key, user.id, db)
            if user_model:
                try:
                    result = await ProviderRouter.call_user_ai_model(user_model, prompt)
                    await ProviderRouter.cache_result(redis_cache_key, prompt, result)
                    return result
                except Exception as e:
                    logger.warning(f"User custom model {model_key} failed: {e}")
                    return f"**Error**: 用户自定义模型 {model_key} 调用失败。错误：{e}"

        model_config = await ModelResolver.get_model_config(model_key, db)
        result = await ProviderRouter.dispatch_with_fallback(prompt, model_config, user, db)

        if not result.startswith("**Error**"):
            await ProviderRouter.cache_result(redis_cache_key, prompt, result)
        else:
            await cache_set(redis_cache_key, result, ttl_seconds=60)

        return result

    @classmethod
    async def generate_portfolio_analysis(
        cls,
        portfolio_items: list,
        market_news: str = None,
        macro_context: str = None,
        model: Optional[str] = None,
        db: AsyncSession = None,
        user_id: str = None,
    ) -> str:
        """生成全量持仓健康诊断报告（带缓存）。"""
        if not portfolio_items:
            return json.dumps({"error": "暂无持仓数据"})

        model_key = model or settings.DEFAULT_AI_MODEL
        user = None
        if user_id and db:
            user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

        holdings_text = "\n".join(
            f"- {h.get('ticker', '?')} ({h.get('name', '')}): "
            f"市值=${h.get('market_value', 0):.2f}, "
            f"盈亏={h.get('pl_percent', 0):.2f}%, "
            f"行业={h.get('sector', '未知')}, "
            f"RRR={h.get('rrr') if h.get('rrr') is not None else 'N/A'}"
            for h in portfolio_items
        )
        prompt = build_portfolio_analysis_prompt(holdings_text, macro_context, market_news)

        prompt_hash = ProviderRouter._hash_prompt(prompt)
        redis_cache_key = f"ai:portfolio:{prompt_hash}"

        import time
        if prompt_hash in ProviderRouter._response_cache:
            cached_response, cached_time = ProviderRouter._response_cache[prompt_hash]
            if time.time() - cached_time < ProviderRouter.RESPONSE_CACHE_TTL:
                logger.info(f"[AI Cache] HIT (memory) for portfolio analysis")
                return cached_response

        cached = await cache_get(redis_cache_key)
        if cached:
            logger.info(f"[AI Cache] HIT (redis) for portfolio analysis")
            ProviderRouter._response_cache[prompt_hash] = (cached, time.time())
            return cached

        if user and db:
            user_model = await ModelResolver.get_user_ai_model(model_key, user.id, db)
            if user_model:
                try:
                    result = await ProviderRouter.call_user_ai_model(user_model, prompt)
                    await ProviderRouter.cache_result(redis_cache_key, prompt, result)
                    return result
                except Exception as e:
                    logger.warning(f"User custom portfolio model {model_key} failed: {e}")
                    return json.dumps({"error": f"AI 服务暂时不可用：{e}"})

        model_config = await ModelResolver.get_model_config(model_key, db)
        result = await ProviderRouter.dispatch_with_fallback(prompt, model_config, user, db)

        if not result.startswith("**Error**") and not result.startswith('{"error"'):
            await ProviderRouter.cache_result(redis_cache_key, prompt, result)

        return result

    @classmethod
    async def generate_text(
        cls,
        prompt: str,
        db: AsyncSession,
        model_key: Optional[str] = None,
        max_tokens: Optional[int] = None,
        extra_params: Optional[dict] = None,
    ) -> str:
        """系统级通用文本生成入口（无用户上下文）。"""
        key = model_key or settings.DEFAULT_AI_MODEL
        model_config = await ModelResolver.get_model_config(key, db)
        return await ProviderRouter.dispatch_with_fallback(
            prompt, model_config, user=None, db=db,
            max_tokens=max_tokens, extra_params=extra_params,
        )

    # Re-export for backwards compatibility
    call_provider = ProviderRouter.call_provider
    test_connection = ProviderRouter.test_connection
    infer_provider_key = ProviderRouter.infer_provider_key
    get_user_ai_model = ModelResolver.get_user_ai_model
    call_user_ai_model = ProviderRouter.call_user_ai_model
    get_default_model_for_provider = ModelResolver.get_default_model_for_provider
    get_model_config = ModelResolver.get_model_config
    normalize_user_model_base_url = staticmethod(ModelResolver.normalize_user_model_base_url)
    _resolve_api_key = staticmethod(ModelResolver.resolve_api_key)


ai_service = AIService
