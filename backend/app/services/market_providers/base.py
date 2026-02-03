from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

class MarketDataProvider(ABC):
    @abstractmethod
    async def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch real-time quote for a ticker.
        Returns: {
            "price": float,
            "change_percent": float,
            "volume": int,
            "last_updated": datetime,
            "status": str
        }
        """
        pass

    @abstractmethod
    async def get_fundamental_data(self, ticker: str) -> Optional[Dict[str, Any]]:
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
    async def get_news(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Fetch latest news for a ticker.
        """
        pass
