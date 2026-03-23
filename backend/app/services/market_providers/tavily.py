import httpx
import asyncio
import logging
from typing import List, Optional, Dict, Any
from app.core.config import settings
from app.schemas.market_data import ProviderNews
from app.services.market_providers.base import MarketDataProvider
from app.utils.time import utc_now_naive

logger = logging.getLogger(__name__)

class TavilyProvider(MarketDataProvider):
    """
    AI Search Provider using Tavily API for high-quality stock news and summaries.
    """
    
    # 类级别信号量：由于 Tavily 免费版对并发极其敏感，强制全系统同时只能有一个请求在进行
    _semaphore = asyncio.Semaphore(1)
    
    def __init__(self, api_key: str | None = None):
        self.api_key = (api_key or settings.TAVILY_API_KEY or "").strip() or None
        self.base_url = "https://api.tavily.com/search"
        if not self.api_key:
            logger.warning("TAVILY_API_KEY not set. TavilyProvider will be disabled.")

    async def get_news(self, ticker: str) -> List[ProviderNews]:
        if not self.api_key:
            return []

        async with self._semaphore:
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
                            publish_time=utc_now_naive()
                        ))
                    
                    return processed_news[:5] # 返回过滤后的前 5 条
            except Exception as e:
                if "432" in str(e):
                    # 仅在第一次或采样记录，避免日志爆炸
                    logger.warning(f"Tavily API Quota Exceeded (432 Error). Returning empty news.")
                else:
                    logger.error(f"Tavily get_news error for {ticker}: {e}")
                return []

    # Implement abstract methods to make the class non-abstract
    async def get_quote(self, ticker: str):
        """Tavily only provides news, return None for quote."""
        return None

    async def get_fundamental_data(self, ticker: str):
        """Tavily only provides news, return None for fundamental."""
        return None

    async def get_historical_data(self, ticker: str, interval: str = "1d", period: str = "1mo"):
        """Tavily only provides news, return None for historical data."""
        return None

    async def get_ohlcv(self, ticker: str, interval: str = "1d", period: str = "1y"):
        """Tavily only provides news, return empty list for OHLCV."""
        return []

    async def get_full_data(self, ticker: str):
        """Tavily only handles news components."""
        return None
