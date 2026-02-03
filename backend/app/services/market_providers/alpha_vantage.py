import requests
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.config import settings
from app.services.market_providers.base import MarketDataProvider

logger = logging.getLogger(__name__)

class AlphaVantageProvider(MarketDataProvider):
    def __init__(self):
        self.api_key = settings.ALPHA_VANTAGE_API_KEY

    async def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None
            
        try:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={self.api_key}"
            response = requests.get(url)
            data = response.json()
            
            quote = data.get("Global Quote")
            if quote:
                return {
                    "price": float(quote.get("05. price", 0)),
                    "change_percent": float(quote.get("10. change percent", "0%").replace("%", "")),
                    "name": ticker,
                    "status": "OPEN" # AV doesn't give clear status in quote
                }
            return None
        except Exception as e:
            logger.error(f"Alpha Vantage get_quote error for {ticker}: {e}")
            return None

    async def get_fundamental_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None
            
        try:
            url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={self.api_key}"
            response = requests.get(url)
            data = response.json()
            
            if not data or "Symbol" not in data:
                return None
                
            return {
                "sector": data.get("Sector"),
                "industry": data.get("Industry"),
                "market_cap": float(data.get("MarketCapitalization", 0)) if data.get("MarketCapitalization") else None,
                "pe_ratio": float(data.get("TrailingPE", 0)) if data.get("TrailingPE") != "None" else None,
                "forward_pe": float(data.get("ForwardPE", 0)) if data.get("ForwardPE") != "None" else None,
                "eps": float(data.get("DilutedEPSTTM", 0)) if data.get("DilutedEPSTTM") != "None" else None,
                "dividend_yield": float(data.get("DividendYield", 0)) if data.get("DividendYield") else None,
                "beta": float(data.get("Beta", 0)) if data.get("Beta") else None,
                "fifty_two_week_high": float(data.get("52WeekHigh", 0)) if data.get("52WeekHigh") else None,
                "fifty_two_week_low": float(data.get("52WeekLow", 0)) if data.get("52WeekLow") else None
            }
        except Exception as e:
            logger.error(f"Alpha Vantage get_fundamental_data error for {ticker}: {e}")
            return None

    async def get_historical_data(self, ticker: str, interval: str = "1d", period: str = "100d") -> Optional[Any]:
        # AV historical data (TIME_SERIES_DAILY) is a bit more complex to parse and usually throttled
        # For now, we rely on yfinance for technical indicators as it's more reliable for bulk data
        return None

    async def get_news(self, ticker: str) -> List[Dict[str, Any]]:
        # AV has NEWS_SENTIMENT, but yfinance is already implemented and works well
        return []
