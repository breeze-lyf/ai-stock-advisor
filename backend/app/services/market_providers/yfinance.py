import yfinance as yf
from datetime import datetime
from typing import Dict, Any, List, Optional
import os
import logging
import asyncio

from app.core.config import settings
from app.services.market_providers.base import MarketDataProvider
from app.services.indicators import TechnicalIndicators
from app.schemas.market_data import (
    ProviderQuote, ProviderFundamental, ProviderNews, 
    ProviderTechnical, FullMarketData, MarketStatus
)

logger = logging.getLogger(__name__)

# Yahoo Finance 数据提供商实现
class YFinanceProvider(MarketDataProvider):
    def __init__(self):
        # 针对 yfinance v1.1.0+ 的更新：其内部已集成 curl_cffi 以解决 Yahoo 的请求限制。
        # 这里不再手动传递 Session 对象，以免引发冲突。
        # 如果配置了 HTTP_PROXY，我们将其注入环境变量供 yfinance (以及 requests/httpx) 使用。
        if settings.HTTP_PROXY:
            os.environ["HTTP_PROXY"] = settings.HTTP_PROXY
            os.environ["HTTPS_PROXY"] = settings.HTTP_PROXY

    async def _run_sync(self, func, *args, **kwargs):
        """
        内部辅助方法：将 yfinance 的同步网络调用封装在线程池中异步运行，避免阻塞事件循环。
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def get_quote(self, ticker: str) -> Optional[ProviderQuote]:
        """抓取实时报价"""
        try:
            tick = yf.Ticker(ticker)
            info = await self._run_sync(getattr, tick, "info") # 线程池调用
            if info and ('currentPrice' in info or 'regularMarketPrice' in info):
                price = info.get('currentPrice') or info.get('regularMarketPrice')
                return ProviderQuote(
                    ticker=ticker,
                    price=float(price),
                    change_percent=float(info.get('regularMarketChangePercent', 0)),
                    name=info.get('shortName', ticker),
                    market_status=MarketStatus.OPEN,
                    last_updated=datetime.utcnow()
                )
            return None
        except Exception as e:
            logger.error(f"yfinance get_quote error for {ticker}: {e}")
            return None

    async def get_fundamental_data(self, ticker: str) -> Optional[ProviderFundamental]:
        """抓取基础面财务数据"""
        try:
            tick = yf.Ticker(ticker)
            info = await self._run_sync(getattr, tick, "info")
            if not info:
                return None
                
            return ProviderFundamental(
                sector=info.get('sector'),
                industry=info.get('industry'),
                market_cap=info.get('marketCap'),
                pe_ratio=info.get('trailingPE'),
                forward_pe=info.get('forwardPE'),
                eps=info.get('trailingEps'),
                dividend_yield=info.get('dividendYield'),
                beta=info.get('beta'),
                fifty_two_week_high=info.get('fiftyTwoWeekHigh'),
                fifty_two_week_low=info.get('fiftyTwoWeekLow')
            )
        except Exception as e:
            logger.error(f"yfinance get_fundamental_data error for {ticker}: {e}")
            return None

    async def get_historical_data(self, ticker: str, interval: str = "1d", period: str = "1mo") -> Optional[Dict[str, Any]]:
        """抓取历史 K 线并计算常用技术指标"""
        try:
            tick = yf.Ticker(ticker)
            hist = await self._run_sync(tick.history, period=period, interval=interval)
            if hist.empty:
                return None
            
            # 使用本地 TechnicalIndicators 类处理 DataFrame 并提取指标
            indicators = TechnicalIndicators.calculate_all(hist)
            return indicators
        except Exception as e:
            logger.error(f"yfinance get_historical_data error for {ticker}: {e}")
            return None

    async def get_news(self, ticker: str) -> List[ProviderNews]:
        """抓取 Yahoo Finance 的最新新闻"""
        try:
            tick = yf.Ticker(ticker)
            news = await self._run_sync(getattr, tick, "news")
            if not news:
                return []
            
            processed_news = []
            for n in news:
                processed_news.append(ProviderNews(
                    id=n.get('uuid'),
                    title=n.get('title'),
                    publisher=n.get('publisher'),
                    link=n.get('link'),
                    publish_time=datetime.utcfromtimestamp(n.get('providerPublishTime', 0))
                ))
            return processed_news
        except Exception as e:
            logger.error(f"yfinance get_news error for {ticker}: {e}")
            return []

    async def get_full_data(self, ticker: str) -> Optional[FullMarketData]:
        """
        针对 YFinance 优化的“全量抓取”，减少 Ticker 对象的实例化开销
        """
        try:
            tick = yf.Ticker(ticker)
            
            # 由于 yfinance 内部请求不是并发的，我们通过 asyncio.gather 在应用侧实现一定的并发抓取
            info_task = self._run_sync(getattr, tick, "info")
            hist_task = self._run_sync(tick.history, period="200d", interval="1d")
            news_task = self._run_sync(getattr, tick, "news")
            
            info, hist, news = await asyncio.gather(info_task, hist_task, news_task, return_exceptions=True)
            
            quote = None
            fundamental = None
            technical = None
            processed_news = []

            # 解析 Info
            if not isinstance(info, Exception) and info:
                price = info.get('currentPrice') or info.get('regularMarketPrice')
                if price:
                    quote = ProviderQuote(
                        ticker=ticker,
                        price=float(price),
                        change_percent=float(info.get('regularMarketChangePercent', 0)),
                        name=info.get('shortName', ticker),
                        market_status=MarketStatus.OPEN,
                        last_updated=datetime.utcnow()
                    )
                    fundamental = ProviderFundamental(
                        sector=info.get('sector'),
                        industry=info.get('industry'),
                        market_cap=info.get('marketCap'),
                        pe_ratio=info.get('trailingPE'),
                        forward_pe=info.get('forwardPE'),
                        eps=info.get('trailingEps'),
                        dividend_yield=info.get('dividendYield'),
                        beta=info.get('beta'),
                        fifty_two_week_high=info.get('fiftyTwoWeekHigh'),
                        fifty_two_week_low=info.get('fiftyTwoWeekLow')
                    )
            
            # 解析 History
            if not isinstance(hist, Exception) and not hist.empty:
                indicators = TechnicalIndicators.calculate_all(hist)
                technical = ProviderTechnical(indicators=indicators)
            
            # 解析 News
            if not isinstance(news, Exception) and news:
                for n in news:
                    processed_news.append(ProviderNews(
                        id=n.get('id', n.get('uuid')),
                        title=n.get('title'),
                        publisher=n.get('publisher'),
                        link=n.get('link'),
                        publish_time=datetime.utcfromtimestamp(n.get('providerPublishTime', 0))
                    ))
            
            # 聚合结果
            if quote:
                return FullMarketData(
                    quote=quote,
                    fundamental=fundamental,
                    technical=technical,
                    news=processed_news
                )
            return None
        except Exception as e:
            logger.error(f"yfinance get_full_data error for {ticker}: {e}")
            return None
