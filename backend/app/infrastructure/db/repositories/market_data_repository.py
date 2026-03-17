import hashlib
import logging
import random
from datetime import datetime
from typing import Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import sanitize_float
from app.models.stock import MarketDataCache, MarketStatus, Stock, StockNews
from app.schemas.market_data import FullMarketData

logger = logging.getLogger(__name__)


class MarketDataRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_market_cache(self, ticker: str) -> Optional[MarketDataCache]:
        stmt = select(MarketDataCache).where(MarketDataCache.ticker == ticker)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def save_changes(self):
        await self.db.commit()

    async def rollback(self):
        await self.db.rollback()

    async def get_latest_news_time(self, ticker: str) -> Optional[datetime]:
        stmt = (
            select(StockNews.publish_time)
            .where(StockNews.ticker == ticker)
            .order_by(StockNews.publish_time.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def persist_market_data(
        self,
        ticker: str,
        data: FullMarketData,
        cache: Optional[MarketDataCache],
        now: datetime,
    ):
        stock_values = {"ticker": ticker, "name": data.quote.name or ticker}
        fundamental = data.fundamental
        if fundamental:
            fields = [
                "sector",
                "industry",
                "market_cap",
                "pe_ratio",
                "forward_pe",
                "eps",
                "dividend_yield",
                "beta",
                "fifty_two_week_high",
                "fifty_two_week_low",
            ]
            for field in fields:
                value = getattr(fundamental, field, None)
                if value is not None:
                    stock_values[field] = value

        await self._upsert_stock(ticker, stock_values)

        cache_values = {
            "ticker": ticker,
            "current_price": sanitize_float(data.quote.price, 0.0),
            "change_percent": sanitize_float(data.quote.change_percent, 0.0),
            "market_status": data.quote.market_status or MarketStatus.OPEN.value,
            "last_updated": now,
        }

        if fundamental:
            cache_values["pe_percentile"] = sanitize_float(fundamental.pe_percentile)
            cache_values["pb_percentile"] = sanitize_float(fundamental.pb_percentile)
            cache_values["net_inflow"] = sanitize_float(fundamental.net_inflow)

        if data.technical and data.technical.indicators:
            self.merge_technical_indicators(cache_values, data.technical.indicators, cache)

        await self._upsert_market_cache(cache, cache_values)
        await self._persist_news(ticker, data, now)
        await self.db.commit()

        return await self.reload_cache(ticker)

    def build_simulation_cache(self, ticker: str, cache: Optional[MarketDataCache], now: datetime):
        if cache:
            fluctuation = 1 + (random.uniform(-0.0005, 0.0005))
            cache.current_price *= fluctuation
            return cache

        return MarketDataCache(
            ticker=ticker,
            current_price=100.0 * (1 + random.uniform(-0.01, 0.01)),
            change_percent=random.uniform(-2.0, 2.0),
            rsi_14=50.0,
            ma_50=100.0,
            ma_200=100.0,
            macd_val=0.0,
            macd_hist=0.0,
            bb_upper=105.0,
            bb_lower=95.0,
            last_updated=datetime(2000, 1, 1),
            market_status=MarketStatus.OPEN,
        )

    @staticmethod
    def merge_technical_indicators(cache_values: dict, indicators: dict, cache: Optional[MarketDataCache]):
        tech_fields = [
            "rsi_14",
            "ma_20",
            "ma_50",
            "ma_200",
            "macd_val",
            "macd_signal",
            "macd_hist",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            "atr_14",
            "k_line",
            "d_line",
            "j_line",
            "volume_ma_20",
            "volume_ratio",
            "macd_hist_slope",
            "macd_cross",
            "macd_is_new_cross",
            "adx_14",
            "pivot_point",
        ]
        for field in tech_fields:
            if field in indicators:
                cache_values[field] = indicators[field]

        resistance = cache_values.get("resistance_1") or (cache.resistance_1 if cache else None) or indicators.get("resistance_1")
        support = cache_values.get("support_1") or (cache.support_1 if cache else None) or indicators.get("support_1")
        current_price = cache_values["current_price"]

        if resistance and support and current_price:
            reward = sanitize_float(resistance) - sanitize_float(current_price)
            risk = sanitize_float(current_price) - sanitize_float(support)

            is_ai = cache.is_ai_strategy if cache else False
            if not is_ai:
                cache_values["resistance_1"] = sanitize_float(indicators.get("resistance_1"))
                cache_values["resistance_2"] = sanitize_float(indicators.get("resistance_2"))
                cache_values["support_1"] = sanitize_float(indicators.get("support_1"))
                cache_values["support_2"] = sanitize_float(indicators.get("support_2"))

            if risk and risk > 0.01:
                cache_values["risk_reward_ratio"] = round(reward / risk, 2) if reward > 0 else 0.0

    async def reload_cache(self, ticker: str):
        try:
            stock_stmt = select(Stock).where(Stock.ticker == ticker)
            stock_res = await self.db.execute(stock_stmt)
            stock = stock_res.scalar_one_or_none()

            cache = await self.get_market_cache(ticker)

            if stock:
                await self.db.refresh(stock)
            if cache:
                await self.db.refresh(cache)
            return cache
        except Exception as exc:
            logger.error(f"Error during db re-fetching/refresh: {exc}")
            return None

    async def _upsert_stock(self, ticker: str, stock_values: dict):
        stock_upsert = pg_insert(Stock).values(stock_values)
        update_cols = {key: value for key, value in stock_values.items() if key != "ticker"}
        if stock_values["name"] == ticker:
            update_cols.pop("name", None)
        stock_upsert = stock_upsert.on_conflict_do_update(index_elements=["ticker"], set_=update_cols)
        await self.db.execute(stock_upsert)

    async def _upsert_market_cache(self, cache: Optional[MarketDataCache], cache_values: dict):
        cache_upsert = pg_insert(MarketDataCache).values(cache_values)
        update_set = {key: value for key, value in cache_values.items() if key != "ticker"}
        if cache and cache.is_ai_strategy:
            for key in ["resistance_1", "resistance_2", "support_1", "support_2", "risk_reward_ratio"]:
                update_set.pop(key, None)
        cache_upsert = cache_upsert.on_conflict_do_update(index_elements=["ticker"], set_=update_set)
        await self.db.execute(cache_upsert)

    async def _persist_news(self, ticker: str, data: FullMarketData, now: datetime):
        if not data.news:
            return

        from sqlalchemy.dialects.postgresql import insert

        news_values = []
        for news in data.news:
            if not news.link:
                continue
            unique_id = hashlib.md5(f"{ticker}:{news.link}".encode()).hexdigest()
            publish_time = news.publish_time or now
            if publish_time.tzinfo:
                publish_time = publish_time.replace(tzinfo=None)

            news_values.append(
                {
                    "id": unique_id,
                    "ticker": ticker,
                    "title": news.title or "无标题",
                    "publisher": news.publisher or "未知媒体",
                    "link": news.link,
                    "summary": news.summary,
                    "publish_time": publish_time,
                }
            )

        if news_values:
            news_stmt = insert(StockNews).values(news_values).on_conflict_do_nothing()
            await self.db.execute(news_stmt)
