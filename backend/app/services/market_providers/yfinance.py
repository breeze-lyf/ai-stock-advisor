import yfinance as yf
from datetime import datetime
from typing import Dict, Any, List, Optional
import os
import logging
import asyncio
import pandas as pd

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
                # 兼容旧版与新版结构
                content = n.get('content', n)
                
                # 获取标题
                title = content.get('title', n.get('title'))
                
                # 获取发布者
                provider = content.get('provider', {})
                publisher = provider.get('displayName') if isinstance(provider, dict) else content.get('publisher', n.get('publisher'))
                
                # 获取链接
                clickthrough = content.get('clickThroughUrl', {})
                link = clickthrough.get('url') if isinstance(clickthrough, dict) else content.get('link', n.get('link'))
                if not link:
                    canonical = content.get('canonicalUrl', {})
                    link = canonical.get('url') if isinstance(canonical, dict) else None
                
                # 获取时间 (兼容 ISO 字符串和时间戳)
                pub_time_raw = content.get('pubDate', content.get('providerPublishTime', n.get('providerPublishTime', 0)))
                if isinstance(pub_time_raw, str):
                    try:
                        # yfinance 新版返回的是 ISO 格式，如 2026-02-03T19:52:54Z
                        publish_time = datetime.fromisoformat(pub_time_raw.replace('Z', '+00:00'))
                    except ValueError:
                        publish_time = datetime.utcnow()
                else:
                    publish_time = datetime.utcfromtimestamp(pub_time_raw)

                processed_news.append(ProviderNews(
                    id=n.get('uuid') or n.get('id'),
                    title=title,
                    publisher=publisher,
                    link=link,
                    publish_time=publish_time
                ))
            return processed_news
        except Exception as e:
            logger.error(f"yfinance get_news error for {ticker}: {e}")
            return []

    async def get_ohlcv(self, ticker: str, interval: str = "1d", period: str = "1y") -> List[Any]:
        """获取原始 K 线数据用于图表展示"""
        try:
            import re
            # 针对 A 股代码进行 Yahoo Finance 格式归一化
            normalized_ticker = ticker
            if re.match(r'^\d{6}$', ticker):
                if ticker.startswith(('6', '9')): normalized_ticker = ticker + ".SS"
                else: normalized_ticker = ticker + ".SZ"
                
            tick = yf.Ticker(normalized_ticker)
            hist = await self._run_sync(tick.history, period=period, interval=interval)
            
            if hist.empty:
                return []
                
            # Add indicators
            hist = TechnicalIndicators.add_historical_indicators(hist)
            
            data = []
            from app.schemas.market_data import OHLCVItem
            for index, row in hist.iterrows():
                # Check for NaN as indicators might have leading NaNs
                rsi_val = float(row['rsi']) if 'rsi' in row and not pd.isna(row['rsi']) else None
                macd_val = float(row['macd']) if 'macd' in row and not pd.isna(row['macd']) else None
                macd_signal = float(row['macd_signal']) if 'macd_signal' in row and not pd.isna(row['macd_signal']) else None
                macd_hist = float(row['macd_hist']) if 'macd_hist' in row and not pd.isna(row['macd_hist']) else None

                data.append(OHLCVItem(
                    time=index.strftime('%Y-%m-%d'),
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=float(row['Volume']) if 'Volume' in row else 0.0,
                    rsi=rsi_val,
                    macd=macd_val,
                    macd_signal=macd_signal,
                    macd_hist=macd_hist
                ))
            return data
        except Exception as e:
            logger.error(f"yfinance get_ohlcv error for {ticker}: {e}")
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
                    # 兼容新旧结构逻辑同上
                    content = n.get('content', n)
                    title = content.get('title', n.get('title'))
                    provider = content.get('provider', {})
                    publisher = provider.get('displayName') if isinstance(provider, dict) else content.get('publisher', n.get('publisher'))
                    
                    clickthrough = content.get('clickThroughUrl', {})
                    link = clickthrough.get('url') if isinstance(clickthrough, dict) else content.get('link', n.get('link'))
                    if not link:
                        canonical = content.get('canonicalUrl', {})
                        link = canonical.get('url') if isinstance(canonical, dict) else None
                    
                    pub_time_raw = content.get('pubDate', content.get('providerPublishTime', n.get('providerPublishTime', 0)))
                    if isinstance(pub_time_raw, str):
                        try:
                            publish_time = datetime.fromisoformat(pub_time_raw.replace('Z', '+00:00'))
                        except ValueError:
                            publish_time = datetime.utcnow()
                    else:
                        publish_time = datetime.utcfromtimestamp(pub_time_raw)

                    processed_news.append(ProviderNews(
                        id=n.get('id', n.get('uuid')),
                        title=title,
                        publisher=publisher,
                        link=link,
                        publish_time=publish_time
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
