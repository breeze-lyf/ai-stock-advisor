"""
Generate Stock Capsule Use Case

Pre-computes lightweight AI digests for a ticker:
  - "news"        : Summarises recent StockNews (25) + GlobalNews (10)
  - "fundamental" : Summarises fundamental/valuation data

These capsules are stored in stock_capsules (upsert) and injected into the
full AI analysis prompt to save tokens and improve coherence.
"""
from __future__ import annotations

import logging
from datetime import datetime
from app.utils.time import utc_now_naive
from typing import Any, Optional, cast

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.prompts import (
    FUNDAMENTAL_CAPSULE_PROMPT_TEMPLATE,
    NEWS_CAPSULE_PROMPT_TEMPLATE,
    TECHNICAL_CAPSULE_PROMPT_TEMPLATE,
)
from app.models.stock_capsule import StockCapsule
from app.models.stock import MarketDataCache, Stock, StockNews
from app.services.ai_service import AIService
from app.services.domain.macro.macro_service import MacroService

logger = logging.getLogger(__name__)

CAPSULE_TYPE_NEWS = "news"
CAPSULE_TYPE_FUNDAMENTAL = "fundamental"
CAPSULE_TYPE_TECHNICAL = "technical"


class GenerateStockCapsuleUseCase:
    """
    Generates (or refreshes) both capsule types for a single ticker.
    Designed to be called:
      - by the scheduler (24h background refresh)
      - on-demand via POST /analysis/{ticker}/capsule/refresh
      - as a pre-step inside AnalyzeStockUseCase
    """

    def __init__(self, db: AsyncSession, ai_service: Optional[AIService] = None):
        self.db = db
        self.ai = ai_service or AIService(db=db)

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    async def generate_news_capsule(self, ticker: str, model: Optional[str] = None) -> Optional[StockCapsule]:
        """Build and persist the news capsule for `ticker`."""
        ticker = ticker.upper().strip()
        model = model or settings.DEFAULT_AI_MODEL

        # Fetch raw news data
        stock_news = await self._get_stock_news(ticker, limit=25)
        global_news = await MacroService.get_latest_news(self.db, limit=10)

        if not stock_news and not global_news:
            logger.info(f"[Capsule] No news data for {ticker}, skipping news capsule.")
            return None

        stock_news_lines = "\n".join(
            [
                f"- [{self._format_datetime(self._get_datetime_attr(n, 'publish_time'))}] "
                f"{self._get_str_attr(n, 'title') or ''} ({self._get_str_attr(n, 'publisher') or ''})"
                for n in stock_news
            ]
        ) or "暂无个股新闻。"

        macro_lines = "\n".join(
            [
                f"- [{self._format_published_at(self._get_attr(n, 'published_at'))}] "
                f"{(self._get_str_attr(n, 'content') or '')[:120]}..."
                for n in global_news
            ]
        ) if global_news else "暂无宏观快讯。"

        prompt = NEWS_CAPSULE_PROMPT_TEMPLATE.format(
            ticker=ticker,
            stock_news_context=stock_news_lines,
            macro_news_context=macro_lines,
        )

        try:
            content = await self._call_ai(prompt, model)
        except Exception as exc:
            logger.error(f"[Capsule] News capsule AI call failed for {ticker}: {exc}")
            return await self._get_existing_capsule(ticker, CAPSULE_TYPE_NEWS)

        if self._is_failed_ai_content(content):
            logger.warning(f"[Capsule] News capsule returned AI error payload for {ticker}, preserving previous capsule.")
            return await self._get_existing_capsule(ticker, CAPSULE_TYPE_NEWS)

        capsule = await self._upsert_capsule(
            ticker=ticker,
            capsule_type=CAPSULE_TYPE_NEWS,
            content=content,
            source_count=len(stock_news) + len(global_news),
            model_used=model,
        )
        logger.info(f"[Capsule] News capsule saved for {ticker} ({len(stock_news)} stock + {len(global_news)} macro headlines)")
        return capsule

    async def generate_fundamental_capsule(self, ticker: str, model: Optional[str] = None) -> Optional[StockCapsule]:
        """Build and persist the fundamental capsule for `ticker`."""
        ticker = ticker.upper().strip()
        model = model or settings.DEFAULT_AI_MODEL

        stock = await self._get_stock(ticker)
        if not stock:
            logger.info(f"[Capsule] No stock row for {ticker}, skipping fundamental capsule.")
            return None

        market_cache = await self._get_market_cache(ticker)
        current_price = self._get_attr(market_cache, "current_price") if market_cache else None

        analyst_parts = []
        buy = self._get_int_attr(stock, "analyst_buy_count") or 0
        hold = self._get_int_attr(stock, "analyst_hold_count") or 0
        sell = self._get_int_attr(stock, "analyst_sell_count") or 0
        total = self._get_int_attr(stock, "analyst_count") or (buy + hold + sell)
        if total > 0:
            analyst_parts.append(f"买入 {buy} / 持有 {hold} / 卖出 {sell}（共 {total} 位）")
        target_price_mean = self._get_float_attr(stock, "target_price_mean")
        if target_price_mean is not None:
            analyst_parts.append(f"目标价 ${target_price_mean:.2f}")
        analyst_summary = "，".join(analyst_parts) or "N/A"

        prompt = FUNDAMENTAL_CAPSULE_PROMPT_TEMPLATE.format(
            ticker=ticker,
            sector=self._get_str_attr(stock, "sector") or "未知",
            industry=self._get_str_attr(stock, "industry") or "未知",
            market_cap=self._get_attr(stock, "market_cap") or "N/A",
            pe_ratio=self._get_attr(stock, "pe_ratio") or "N/A",
            forward_pe=self._get_attr(stock, "forward_pe") or "N/A",
            beta=self._get_attr(stock, "beta") or "N/A",
            fifty_two_week_low=self._get_attr(stock, "fifty_two_week_low") or "N/A",
            fifty_two_week_high=self._get_attr(stock, "fifty_two_week_high") or "N/A",
            analyst_summary=analyst_summary,
            current_price=current_price or "N/A",
        )

        try:
            content = await self._call_ai(prompt, model)
        except Exception as exc:
            logger.error(f"[Capsule] Fundamental capsule AI call failed for {ticker}: {exc}")
            return await self._get_existing_capsule(ticker, CAPSULE_TYPE_FUNDAMENTAL)

        if self._is_failed_ai_content(content):
            logger.warning(f"[Capsule] Fundamental capsule returned AI error payload for {ticker}, preserving previous capsule.")
            return await self._get_existing_capsule(ticker, CAPSULE_TYPE_FUNDAMENTAL)

        capsule = await self._upsert_capsule(
            ticker=ticker,
            capsule_type=CAPSULE_TYPE_FUNDAMENTAL,
            content=content,
            source_count=1,
            model_used=model,
        )
        logger.info(f"[Capsule] Fundamental capsule saved for {ticker}")
        return capsule

    async def generate_technical_capsule(self, ticker: str, model: Optional[str] = None) -> Optional[StockCapsule]:
        """Build and persist the technical capsule for `ticker`."""
        ticker = ticker.upper().strip()
        model = model or settings.DEFAULT_AI_MODEL

        market_cache = await self._get_market_cache(ticker)
        if not market_cache:
            logger.info(f"[Capsule] No market cache for {ticker}, skipping technical capsule.")
            return None

        def _v(val, fmt=".2f"):
            return format(val, fmt) if val is not None else "N/A"

        prompt = TECHNICAL_CAPSULE_PROMPT_TEMPLATE.format(
            ticker=ticker,
            current_price=_v(market_cache.current_price),
            change_percent=_v(getattr(market_cache, "change_percent", None), ".2f"),
            ma_20=_v(getattr(market_cache, "ma_20", None)),
            ma_50=_v(getattr(market_cache, "ma_50", None)),
            ma_200=_v(getattr(market_cache, "ma_200", None)),
            macd_val=_v(getattr(market_cache, "macd_val", None)),
            macd_signal=_v(getattr(market_cache, "macd_signal", None)),
            macd_hist=_v(getattr(market_cache, "macd_hist", None)),
            macd_hist_slope=_v(getattr(market_cache, "macd_hist_slope", None)),
            macd_cross=getattr(market_cache, "macd_cross", None) or "N/A",
            rsi_14=_v(getattr(market_cache, "rsi_14", None)),
            k_line=_v(getattr(market_cache, "k_line", None)),
            d_line=_v(getattr(market_cache, "d_line", None)),
            j_line=_v(getattr(market_cache, "j_line", None)),
            bb_upper=_v(getattr(market_cache, "bb_upper", None)),
            bb_middle=_v(getattr(market_cache, "bb_middle", None)),
            bb_lower=_v(getattr(market_cache, "bb_lower", None)),
            atr_14=_v(getattr(market_cache, "atr_14", None)),
            adx_14=_v(getattr(market_cache, "adx_14", None)),
            volume_ratio=_v(getattr(market_cache, "volume_ratio", None)),
            resistance_1=_v(getattr(market_cache, "resistance_1", None)),
            support_1=_v(getattr(market_cache, "support_1", None)),
        )

        try:
            content = await self._call_ai(prompt, model)
        except Exception as exc:
            logger.error(f"[Capsule] Technical capsule AI call failed for {ticker}: {exc}")
            return await self._get_existing_capsule(ticker, CAPSULE_TYPE_TECHNICAL)

        if self._is_failed_ai_content(content):
            logger.warning(f"[Capsule] Technical capsule returned AI error payload for {ticker}, preserving previous capsule.")
            return await self._get_existing_capsule(ticker, CAPSULE_TYPE_TECHNICAL)

        capsule = await self._upsert_capsule(
            ticker=ticker,
            capsule_type=CAPSULE_TYPE_TECHNICAL,
            content=content,
            source_count=1,
            model_used=model,
        )
        logger.info(f"[Capsule] Technical capsule saved for {ticker}")
        return capsule

    async def generate_all(self, ticker: str, model: Optional[str] = None) -> dict[str, Optional[StockCapsule]]:
        """Generate all three capsule types and return them as a dict."""
        news = await self.generate_news_capsule(ticker, model)
        fundamental = await self.generate_fundamental_capsule(ticker, model)
        technical = await self.generate_technical_capsule(ticker, model)
        return {CAPSULE_TYPE_NEWS: news, CAPSULE_TYPE_FUNDAMENTAL: fundamental, CAPSULE_TYPE_TECHNICAL: technical}

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_capsules(self, ticker: str) -> dict[str, Optional[StockCapsule]]:
        """Return all capsule types for a ticker (None if not yet generated)."""
        ticker = ticker.upper().strip()
        stmt = select(StockCapsule).where(StockCapsule.ticker == ticker)
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        out: dict[str, Optional[StockCapsule]] = {
            CAPSULE_TYPE_NEWS: None,
            CAPSULE_TYPE_FUNDAMENTAL: None,
            CAPSULE_TYPE_TECHNICAL: None,
        }
        for row in rows:
            capsule_type = self._get_str_attr(row, "capsule_type")
            if capsule_type in out:
                out[capsule_type] = row
        return out

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _call_ai(self, prompt: str, model: str) -> str:
        return await self.ai.call_with_fallback(prompt, model)

    def _is_failed_ai_content(self, content: Optional[str]) -> bool:
        normalized = (content or "").strip()
        lowered = normalized.lower()
        return (
            not normalized
            or normalized.startswith("**Error**")
            or lowered.startswith("error:")
            or lowered.startswith('{"error"')
        )

    async def _get_existing_capsule(self, ticker: str, capsule_type: str) -> Optional[StockCapsule]:
        stmt = select(StockCapsule).where(
            StockCapsule.ticker == ticker,
            StockCapsule.capsule_type == capsule_type,
        )
        result = await self.db.execute(stmt)
        capsule = result.scalar_one_or_none()
        if capsule and self._is_failed_ai_content(capsule.content):
            return None
        return capsule

    def _get_attr(self, obj: Any, attr: str) -> Any:
        if obj is None:
            return None
        return cast(Any, getattr(obj, attr, None))

    def _get_str_attr(self, obj: Any, attr: str) -> Optional[str]:
        value = self._get_attr(obj, attr)
        return value if isinstance(value, str) else None

    def _get_int_attr(self, obj: Any, attr: str) -> Optional[int]:
        value = self._get_attr(obj, attr)
        return value if isinstance(value, int) else None

    def _get_float_attr(self, obj: Any, attr: str) -> Optional[float]:
        value = self._get_attr(obj, attr)
        return value if isinstance(value, (int, float)) else None

    def _get_datetime_attr(self, obj: Any, attr: str) -> Optional[datetime]:
        value = self._get_attr(obj, attr)
        return value if isinstance(value, datetime) else None

    def _format_datetime(self, value: Optional[datetime]) -> str:
        return value.strftime('%m-%d %H:%M') if value is not None else ''

    def _format_published_at(self, value: Any) -> str:
        if isinstance(value, str):
            return value[:16]
        if isinstance(value, datetime):
            return value.strftime('%m-%d %H:%M')
        return ''

    async def _get_stock_news(self, ticker: str, limit: int = 25):
        stmt = (
            select(StockNews)
            .where(StockNews.ticker == ticker)
            .order_by(StockNews.publish_time.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def _get_stock(self, ticker: str):
        result = await self.db.execute(select(Stock).where(Stock.ticker == ticker))
        return result.scalar_one_or_none()

    async def _get_market_cache(self, ticker: str):
        result = await self.db.execute(select(MarketDataCache).where(MarketDataCache.ticker == ticker))
        return result.scalar_one_or_none()

    async def _upsert_capsule(
        self,
        ticker: str,
        capsule_type: str,
        content: str,
        source_count: int,
        model_used: str,
    ) -> StockCapsule:
        """Insert or update the capsule row (upsert on ticker+capsule_type)."""
        now = utc_now_naive()

        stmt = (
            pg_insert(StockCapsule)
            .values(
                ticker=ticker,
                capsule_type=capsule_type,
                content=content,
                source_count=source_count,
                model_used=model_used,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_stock_capsules_ticker_type",
                set_={
                    "content": content,
                    "source_count": source_count,
                    "model_used": model_used,
                    "updated_at": now,
                },
            )
            .returning(StockCapsule)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one()
