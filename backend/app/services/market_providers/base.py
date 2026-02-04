from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.schemas.market_data import ProviderQuote, ProviderFundamental, ProviderNews, FullMarketData

class MarketDataProvider(ABC):
    @abstractmethod
    async def get_quote(self, ticker: str) -> Optional[ProviderQuote]:
        """
        Fetch real-time quote for a ticker.
        """
        pass

    @abstractmethod
    async def get_fundamental_data(self, ticker: str) -> Optional[ProviderFundamental]:
        """
        Fetch fundamental data (PE, Market Cap, EPS, etc.).
        """
        pass

    @abstractmethod
    async def get_historical_data(self, ticker: str, interval: str = "1d", period: str = "1mo") -> Optional[Any]:
        """
        Fetch historical price data for indicator calculation.
        """
        pass

    @abstractmethod
    async def get_news(self, ticker: str) -> List[ProviderNews]:
        """
        Fetch latest news for a ticker.
        """
        pass

    async def get_full_data(self, ticker: str) -> Optional[FullMarketData]:
        """
        Optional specialized implementation to fetch everything in one go.
        Defaults to individual calls.
        """
        return None
