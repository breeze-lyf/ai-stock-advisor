from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging
from typing import Optional

from app.infrastructure.db.repositories.market_data_repository import MarketDataRepository
from app.models.stock import MarketDataCache
from app.schemas.market_data import FullMarketData
from app.services.market_data_fetcher import MarketDataFetcher
from app.services.market_data_policy import MarketDataCachePolicy

logger = logging.getLogger(__name__)

# 市场数据分析中台 (Market Data Service Hub)
# 职责：负责从外部获取行情、技术指标、新闻，处理数据缓存，并把信息同步到数据库中。
# 这是本项目的“行情发动机”。
class MarketDataService:
    @staticmethod
    def _repo(db: AsyncSession) -> MarketDataRepository:
        return MarketDataRepository(db)

    @staticmethod
    async def get_real_time_data(ticker: str, db: AsyncSession, preferred_source: str = "AKSHARE", force_refresh: bool = False, price_only: bool = False, skip_news: bool = False):
        """
        核心方法：获取单支股票最新的行情。支持 price_only 模式以提高响应速度。
        """
        if ticker.lower() == "portfolio":
            return None

        now = datetime.utcnow()
        repo = MarketDataService._repo(db)
        cache = await repo.get_market_cache(ticker)
        if MarketDataCachePolicy.can_use_cache(cache, now, force_refresh, price_only):
            return cache

        latest_news_time = await repo.get_latest_news_time(ticker)
        skip_news = MarketDataCachePolicy.should_skip_news(latest_news_time, force_refresh, skip_news, now)
        data = await MarketDataService.fetch_market_data(
            ticker,
            preferred_source,
            price_only=price_only,
            skip_news=skip_news,
        )

        if not data:
            if cache:
                logger.warning(f"{ticker} 实时刷新失败，回退到使用现有缓存数据。")
                return cache
            
            cache = repo.build_simulation_cache(ticker, cache, now)
            await repo.save_changes()
            return cache

        return await repo.persist_market_data(ticker, data, cache, now)

    @staticmethod
    async def fetch_market_data(
        ticker: str,
        preferred_source: str,
        price_only: bool = False,
        skip_news: bool = False,
    ) -> Optional[FullMarketData]:
        return await MarketDataFetcher.fetch_from_providers(
            ticker,
            preferred_source,
            price_only=price_only,
            skip_news=skip_news,
        )

    @staticmethod
    async def persist_market_data(
        ticker: str,
        data: FullMarketData,
        cache: Optional[MarketDataCache],
        db: AsyncSession,
        now: datetime,
    ):
        return await MarketDataService._repo(db).persist_market_data(ticker, data, cache, now)

    @staticmethod
    def build_simulation_cache(ticker: str, cache: Optional[MarketDataCache], now: datetime):
        return MarketDataRepository(None).build_simulation_cache(ticker, cache, now)

    @staticmethod
    async def _fetch_from_providers(ticker: str, preferred_source: str, price_only: bool = False, skip_news: bool = False) -> Optional[FullMarketData]:
        return await MarketDataService.fetch_market_data(
            ticker,
            preferred_source,
            price_only=price_only,
            skip_news=skip_news,
        )

    @staticmethod
    async def _update_database(ticker: str, data: FullMarketData, cache: Optional[MarketDataCache], db: AsyncSession, now: datetime):
        return await MarketDataService.persist_market_data(ticker, data, cache, db, now)

    @staticmethod
    async def _handle_simulation(ticker: str, cache: Optional[MarketDataCache], now: datetime):
        return MarketDataService.build_simulation_cache(ticker, cache, now)
