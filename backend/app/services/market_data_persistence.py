from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.market_data_repository import MarketDataRepository
from app.models.stock import MarketDataCache
from app.schemas.market_data import FullMarketData


class MarketDataPersistence:
    @staticmethod
    async def get_market_cache(db: AsyncSession, ticker: str) -> Optional[MarketDataCache]:
        return await MarketDataRepository(db).get_market_cache(ticker)

    @staticmethod
    async def get_latest_news_time(db: AsyncSession, ticker: str) -> Optional[datetime]:
        return await MarketDataRepository(db).get_latest_news_time(ticker)

    @staticmethod
    async def persist_market_data(
        ticker: str,
        data: FullMarketData,
        cache: Optional[MarketDataCache],
        db: AsyncSession,
        now: datetime,
    ):
        return await MarketDataRepository(db).persist_market_data(ticker, data, cache, now)

    @staticmethod
    def build_simulation_cache(ticker: str, cache: Optional[MarketDataCache], now: datetime):
        return MarketDataRepository(None).build_simulation_cache(ticker, cache, now)

    @staticmethod
    def _merge_technical_indicators(cache_values: dict, indicators: dict, cache: Optional[MarketDataCache]):
        return MarketDataRepository.merge_technical_indicators(cache_values, indicators, cache)
