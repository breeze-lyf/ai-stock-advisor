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

class YFinanceProvider(MarketDataProvider):
    def __init__(self):
        # We no longer pass a custom session to Ticker because newer yfinance (1.1.0+)
        # uses curl_cffi internally for Yahoo and manual sessions can cause conflicts.
        # Proxies are handled via environment variables which yfinance respects.
        if settings.HTTP_PROXY:
            os.environ["HTTP_PROXY"] = settings.HTTP_PROXY
            os.environ["HTTPS_PROXY"] = settings.HTTP_PROXY

    async def _run_sync(self, func, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def get_quote(self, ticker: str) -> Optional[ProviderQuote]:
        try:
            tick = yf.Ticker(ticker)
            info = await self._run_sync(getattr, tick, "info")
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
        try:
            tick = yf.Ticker(ticker)
            hist = await self._run_sync(tick.history, period=period, interval=interval)
            if hist.empty:
                return None
            
            indicators = TechnicalIndicators.calculate_all(hist)
            return indicators
        except Exception as e:
            logger.error(f"yfinance get_historical_data error for {ticker}: {e}")
            return None

    async def get_news(self, ticker: str) -> List[ProviderNews]:
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
        try:
            tick = yf.Ticker(ticker)
            
            info_task = self._run_sync(getattr, tick, "info")
            hist_task = self._run_sync(tick.history, period="200d", interval="1d")
            news_task = self._run_sync(getattr, tick, "news")
            
            info, hist, news = await asyncio.gather(info_task, hist_task, news_task, return_exceptions=True)
            
            quote = None
            fundamental = None
            technical = None
            processed_news = []

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
            
            if not isinstance(hist, Exception) and not hist.empty:
                indicators = TechnicalIndicators.calculate_all(hist)
                technical = ProviderTechnical(indicators=indicators)
            
            if not isinstance(news, Exception) and news:
                for n in news:
                    processed_news.append(ProviderNews(
                        id=n.get('id', n.get('uuid')),
                        title=n.get('title'),
                        publisher=n.get('publisher'),
                        link=n.get('link'),
                        publish_time=datetime.utcfromtimestamp(n.get('providerPublishTime', 0))
                    ))
            
            if isinstance(info, Exception):
                logger.error(f"yfinance info task error for {ticker}: {info}")
            if isinstance(hist, Exception):
                logger.error(f"yfinance history task error for {ticker}: {hist}")
            if isinstance(news, Exception):
                logger.error(f"yfinance news task error for {ticker}: {news}")

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
