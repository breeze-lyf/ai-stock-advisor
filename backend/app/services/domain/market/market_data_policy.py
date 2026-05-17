from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.models.stock import MarketDataCache

logger = logging.getLogger(__name__)


class MarketDataCachePolicy:
    @staticmethod
    def can_use_cache(
        cache: MarketDataCache | None,
        now: datetime,
        force_refresh: bool,
        price_only: bool,
    ) -> bool:
        if force_refresh or not cache:
            return False
        if (now - cache.last_updated) >= timedelta(minutes=1):
            return False
        return price_only or cache.rsi_14 is not None

    @staticmethod
    def should_skip_news(
        latest_news_time: Optional[datetime],
        force_refresh: bool,
        skip_news: bool,
        now: datetime,
    ) -> bool:
        if skip_news or not force_refresh:
            return skip_news
        if latest_news_time and (now - latest_news_time).total_seconds() < 12 * 3600:
            logger.info("Skipping Tavily news fetch because local news is updated within 12 hours.")
            return True
        return False
