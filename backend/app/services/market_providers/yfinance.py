import yfinance as yf
from requests import Session
from datetime import datetime
from typing import Dict, Any, List, Optional
import os
import logging

from app.core.config import settings
from app.services.market_providers.base import MarketDataProvider
from app.services.indicators import TechnicalIndicators

logger = logging.getLogger(__name__)

class YFinanceProvider(MarketDataProvider):
    def __init__(self):
        self._session = Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        if settings.HTTP_PROXY:
            os.environ["HTTP_PROXY"] = settings.HTTP_PROXY
            os.environ["HTTPS_PROXY"] = settings.HTTP_PROXY

    async def get_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        try:
            tick = yf.Ticker(ticker, session=self._session)
            info = tick.info
            if info and ('currentPrice' in info or 'regularMarketPrice' in info):
                return {
                    "price": info.get('currentPrice') or info.get('regularMarketPrice'),
                    "change_percent": info.get('regularMarketChangePercent', 0),
                    "name": info.get('shortName', ticker),
                    "status": "OPEN" # yfinance info doesn't give clear status easily
                }
            return None
        except Exception as e:
            logger.error(f"yfinance get_quote error for {ticker}: {e}")
            return None

    async def get_fundamental_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        try:
            tick = yf.Ticker(ticker, session=self._session)
            info = tick.info
            if not info:
                return None
                
            return {
                "sector": info.get('sector'),
                "industry": info.get('industry'),
                "market_cap": info.get('marketCap'),
                "pe_ratio": info.get('trailingPE'),
                "forward_pe": info.get('forwardPE'),
                "eps": info.get('trailingEps'),
                "dividend_yield": info.get('dividendYield'),
                "beta": info.get('beta'),
                "fifty_two_week_high": info.get('fiftyTwoWeekHigh'),
                "fifty_two_week_low": info.get('fiftyTwoWeekLow')
            }
        except Exception as e:
            logger.error(f"yfinance get_fundamental_data error for {ticker}: {e}")
            return None

    async def get_historical_data(self, ticker: str, interval: str = "1d", period: str = "100d") -> Optional[Dict[str, Any]]:
        try:
            tick = yf.Ticker(ticker, session=self._session)
            hist = tick.history(period=period, interval=interval)
            if hist.empty:
                return None
            
            indicators = TechnicalIndicators.calculate_all(hist)
            return indicators
        except Exception as e:
            logger.error(f"yfinance get_historical_data error for {ticker}: {e}")
            return None

    async def get_news(self, ticker: str) -> List[Dict[str, Any]]:
        try:
            tick = yf.Ticker(ticker, session=self._session)
            news = tick.news
            if not news:
                return []
            
            processed_news = []
            for n in news:
                processed_news.append({
                    "id": n.get('uuid'),
                    "title": n.get('title'),
                    "publisher": n.get('publisher'),
                    "link": n.get('link'),
                    "publish_time": datetime.utcfromtimestamp(n.get('providerPublishTime', 0))
                })
            return processed_news
        except Exception as e:
            logger.error(f"yfinance get_news error for {ticker}: {e}")
            return []
