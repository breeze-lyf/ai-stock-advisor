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
                # 优化 1: 更精准的搜索词，包含 ticker 和 stock news 关键字
                query = f"ticker:{ticker} stock news financial headlines"
                payload = {
                    "api_key": self.api_key,
                    "query": query,
                    "topic": "news", 
                    "search_depth": "basic",
                    "include_answer": False,
                    "include_images": False,
                    "max_results": 10 # 抓多几个以便过滤
                }
                
                response = await client.post(self.base_url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                results = data.get("results", [])
                processed_news = []
                
                # 优化 2: 强制过滤逻辑 (Post-Filtering)
                # 新闻标题或摘要必须包含 ticker
                ticker_lower = ticker.lower()
                
                for idx, res in enumerate(results):
                    title = res.get("title", "")
                    content = res.get("content", "")
                    
                    # 只有内容中确实提到了这个代码，才认为是相关的
                    is_relevant = (ticker_lower in title.lower()) or (ticker_lower in content.lower())
                    
                    if not is_relevant:
                        # 容错：有些新闻可能不带 $, 直接写公司简称。
                        # 我们目前只做最硬的限制，防止 Apple/Amazon 这种大词漂移
                        continue

                    url = res.get("url", "")
                    import hashlib
                    unique_id = hashlib.md5(url.encode()).hexdigest() if url else f"fallback-{idx}"
                    
                    processed_news.append(ProviderNews(
                        id=f"tavily-{unique_id}",
                        title=title,
                        publisher=res.get("url").split("/")[2] if res.get("url") else "Tavily Search",
                        link=res.get("url"),
                        summary=content,
                        publish_time=datetime.utcnow()
                    ))
                
                return processed_news[:5] # 返回过滤后的前 5 条
        except Exception as e:
            logger.error(f"Tavily get_news error for {ticker}: {e}")
            return []

    # Other methods are not primary for Tavily
    async def get_quote(self, ticker: str): return None
    async def get_fundamental_data(self, ticker: str): return None
    async def get_historical_data(self, ticker: str, interval: str = "1d", period: str = "1mo"): return None
    async def get_ohlcv(self, ticker: str, interval: str = "1d", period: str = "1y"): return []
    async def get_full_data(self, ticker: str): return None
