import httpx
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.core.config import settings
from app.schemas.market_data import ProviderNews
from app.services.market_providers.base import MarketDataProvider

logger = logging.getLogger(__name__)

class TavilyProvider(MarketDataProvider):
    """
    AI Search Provider using Tavily API for high-quality stock news and summaries.
    """
    
    def __init__(self):
        self.api_key = settings.TAVILY_API_KEY
        self.base_url = "https://api.tavily.com/search"
        if not self.api_key:
            logger.warning("TAVILY_API_KEY not set. TavilyProvider will be disabled.")

    async def get_news(self, ticker: str) -> List[ProviderNews]:
        if not self.api_key:
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Search for latest news about the stock ticker
                query = f"latest business and financial news for {ticker} stock"
                payload = {
                    "api_key": self.api_key,
                    "query": query,
                    "search_depth": "news", # Use specialized news search
                    "include_answer": False,
                    "include_images": False,
                    "max_results": 5
                }
                
                response = await client.post(self.base_url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                processed_news = []
                
                for idx, res in enumerate(results):
                    # Tavily results don't always have a strict 'publish_time', 
                    # use current time as fallback if missing or parse from context
                    processed_news.append(ProviderNews(
                        id=f"tavily-{ticker}-{idx}",
                        title=res.get("title"),
                        publisher=res.get("url").split("/")[2] if res.get("url") else "Tavily Search",
                        link=res.get("url"),
                        summary=res.get("content"),
                        publish_time=datetime.utcnow() # Fallback
                    ))
                
                return processed_news
        except Exception as e:
            logger.error(f"Tavily get_news error for {ticker}: {e}")
            return []

    # Other methods are not primary for Tavily
    async def get_quote(self, ticker: str): return None
    async def get_fundamental_data(self, ticker: str): return None
    async def get_historical_data(self, ticker: str): return None
    async def get_full_data(self, ticker: str): return None
