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
from app.services.model_resolver import ModelResolver
from app.services.provider_router import ProviderRouter

logger = logging.getLogger(__name__)


class AIService:
    """AI 分析服务 — 纯编排，不包含底层 provider 调用细节。

    实例化路径（新代码推荐）：
        ai = AIService(db=db, user=current_user)
        result = await ai.generate_analysis(ticker="AAPL", ...)

    类方法路径（向后兼容）：
        result = await AIService.generate_analysis(ticker="AAPL", ..., db=db, user_id=...)
    """

    def __init__(self, db: AsyncSession = None, user: User = None):
        self.db = db
        self.user = user

    # ------------------------------------------------------------------
    #  内部辅助
    # ------------------------------------------------------------------

    async def _resolve_user(self, user_id: str = None) -> User | None:
        """加载用户上下文（如果尚未加载）。"""
        if self.user:
            return self.user
        if user_id and self.db:
            try:
                self.user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
            except Exception as e:
                logger.warning(f"Failed to get user info: {e}")
        return self.user

    async def call_with_fallback(
        self,
        prompt: str,
        model_key: str,
        max_tokens: Optional[int] = None,
        extra_params: Optional[dict] = None,
    ) -> str:
        """统一入口：用户自定义模型 → 系统供应商回退。

        与 ProviderRouter.dispatch_with_fallback 的区别：
        本方法在调用前先检查用户的自定义模型配置，命中则直接走用户模型；
        未命中（或无用户上下文）则回退到系统供应商表。
        """
        # 1. 用户自定义模型优先
        if self.user and self.db:
            user_model = await ModelResolver.get_user_ai_model(model_key, self.user.id, self.db)
            if user_model:
                try:
                    return await ProviderRouter.call_user_ai_model(user_model, prompt)
                except Exception as e:
                    logger.warning(f"User custom model {model_key} failed: {e}")
                    return f"**Error**: 用户自定义模型 {model_key} 调用失败。错误：{e}"

        # 2. 系统供应商回退
        model_config = await ModelResolver.get_model_config(model_key, self.db)
        return await ProviderRouter.dispatch_with_fallback(
            prompt, model_config, user=self.user, db=self.db,
            max_tokens=max_tokens, extra_params=extra_params,
        )

    # ------------------------------------------------------------------
    #  缓存工具（内部使用）
    # ------------------------------------------------------------------

    @staticmethod
    def _check_memory_cache(prompt_hash: str) -> str | None:
        cached = ProviderRouter._response_cache.get(prompt_hash)
        if cached:
            cached_response, cached_time = cached
            import time
            if time.time() - cached_time < ProviderRouter.RESPONSE_CACHE_TTL:
                return cached_response
        return None

    @staticmethod
    def _write_memory_cache(prompt_hash: str, result: str):
        import time
        ProviderRouter._response_cache[prompt_hash] = (result, time.time())

    # ------------------------------------------------------------------
    #  generate_analysis
    # ------------------------------------------------------------------

    async def generate_analysis(
        self,
        ticker: str,
        market_data: dict,
        news_data: list = None,
        macro_context: str = None,
        fundamental_data: dict = None,
        previous_analysis: dict = None,
        model: Optional[str] = None,
        fomc_days_away: int = None,
        next_fomc_date: str = None,
        earnings_date: str = None,
        vix_level: float = None,
        analyst_summary: str = None,
        pre_computed_news: str = None,
        pre_computed_fundamental: str = None,
    ) -> str:
        """生成个股深度诊断（带缓存）。"""
        model_key = model or settings.DEFAULT_AI_MODEL

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

        cached = self._check_memory_cache(prompt_hash)
        if cached:
            logger.info(f"[AI Cache] HIT (memory) for {ticker}")
            return cached

        cached = await cache_get(redis_cache_key)
        if cached:
            logger.info(f"[AI Cache] HIT (redis) for {ticker}")
            self._write_memory_cache(prompt_hash, cached)
            return cached

        result = await self.call_with_fallback(prompt, model_key)

        if not result.startswith("**Error**"):
            await ProviderRouter.cache_result(redis_cache_key, prompt, result)
        else:
            await cache_set(redis_cache_key, result, ttl_seconds=60)

        return result

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
        """类方法包装 — 构造实例后委托。"""
        inst = cls(db=db)
        await inst._resolve_user(user_id)
        return await inst.generate_analysis(
            ticker=ticker,
            market_data=market_data,
            news_data=news_data,
            macro_context=macro_context,
            fundamental_data=fundamental_data,
            previous_analysis=previous_analysis,
            model=model,
            fomc_days_away=fomc_days_away,
            next_fomc_date=next_fomc_date,
            earnings_date=earnings_date,
            vix_level=vix_level,
            analyst_summary=analyst_summary,
            pre_computed_news=pre_computed_news,
            pre_computed_fundamental=pre_computed_fundamental,
        )

    # ------------------------------------------------------------------
    #  generate_portfolio_analysis
    # ------------------------------------------------------------------

    async def generate_portfolio_analysis(
        self,
        portfolio_items: list,
        market_news: str = None,
        macro_context: str = None,
        model: Optional[str] = None,
    ) -> str:
        """生成全量持仓健康诊断报告（带缓存）。"""
        if not portfolio_items:
            return json.dumps({"error": "暂无持仓数据"})

        model_key = model or settings.DEFAULT_AI_MODEL

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

        cached = self._check_memory_cache(prompt_hash)
        if cached:
            logger.info(f"[AI Cache] HIT (memory) for portfolio analysis")
            return cached

        cached = await cache_get(redis_cache_key)
        if cached:
            logger.info(f"[AI Cache] HIT (redis) for portfolio analysis")
            self._write_memory_cache(prompt_hash, cached)
            return cached

        result = await self.call_with_fallback(prompt, model_key)

        if not result.startswith("**Error**") and not result.startswith('{"error"'):
            await ProviderRouter.cache_result(redis_cache_key, prompt, result)

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
        """类方法包装 — 构造实例后委托。"""
        inst = cls(db=db)
        await inst._resolve_user(user_id)
        return await inst.generate_portfolio_analysis(
            portfolio_items=portfolio_items,
            market_news=market_news,
            macro_context=macro_context,
            model=model,
        )

    # ------------------------------------------------------------------
    #  generate_text
    # ------------------------------------------------------------------

    async def generate_text(
        self,
        prompt: str,
        model_key: Optional[str] = None,
        max_tokens: Optional[int] = None,
        extra_params: Optional[dict] = None,
    ) -> str:
        """通用文本生成入口（实例方法 — 使用 self.db / self.user）。"""
        key = model_key or settings.DEFAULT_AI_MODEL
        return await self.call_with_fallback(prompt, key, max_tokens=max_tokens, extra_params=extra_params)

    @classmethod
    async def generate_text(
        cls,
        prompt: str,
        db: AsyncSession,
        model_key: Optional[str] = None,
        max_tokens: Optional[int] = None,
        extra_params: Optional[dict] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """类方法包装 — 构造实例后委托。"""
        inst = cls(db=db)
        await inst._resolve_user(user_id)
        return await inst.generate_text(
            prompt=prompt,
            model_key=model_key,
            max_tokens=max_tokens,
            extra_params=extra_params,
        )

    # ------------------------------------------------------------------
    #  向后兼容导出
    # ------------------------------------------------------------------

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
