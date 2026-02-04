from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
import asyncio
import logging
from typing import Optional, Dict, Any, List

from app.core.config import settings
from app.models.stock import Stock, MarketDataCache, MarketStatus, StockNews
from app.services.market_providers import ProviderFactory
from app.schemas.market_data import FullMarketData

logger = logging.getLogger(__name__)

class MarketDataService:
    @staticmethod
    async def get_real_time_data(ticker: str, db: AsyncSession, preferred_source: str = "YFINANCE", force_refresh: bool = False):
        # 1. Check Cache
        stmt = select(MarketDataCache).where(MarketDataCache.ticker == ticker)
        result = await db.execute(stmt)
        cache = result.scalar_one_or_none()

        now = datetime.utcnow()
        if not force_refresh and cache and (now - cache.last_updated) < timedelta(minutes=1):
            return cache

        # 2. Fetch Data from Providers
        data = await MarketDataService._fetch_from_providers(ticker, preferred_source)

        if not data:
            cache = await MarketDataService._handle_simulation(ticker, cache, now)
            await db.commit()
            return cache

        # 3. Update/Create DB records
        return await MarketDataService._update_database(ticker, data, cache, db, now)

    @staticmethod
    async def _fetch_from_providers(ticker: str, preferred_source: str) -> Optional[FullMarketData]:
        provider = ProviderFactory.get_provider(ticker, preferred_source)
        
        # Try full optimization first
        result = await provider.get_full_data(ticker)
        if result:
            return result

        # Prepare tasks (Parallel)
        try:
            quote_task = provider.get_quote(ticker)
            fundamental_task = provider.get_fundamental_data(ticker)
            indicator_task = provider.get_historical_data(ticker, period="200d")
            
            # AI News Enrichment (Tavily)
            from app.services.market_providers.tavily import TavilyProvider
            tavily = TavilyProvider()
            news_task = tavily.get_news(ticker) if tavily.api_key else provider.get_news(ticker)
            
            res = await asyncio.gather(quote_task, fundamental_task, indicator_task, news_task, return_exceptions=True)
            quote, fundamental, indicators, news = res
            
            if not isinstance(quote, Exception) and quote:
                # If we have a quote, we have a valid data point
                return FullMarketData(
                    quote=quote,
                    fundamental=fundamental if not isinstance(fundamental, Exception) else None,
                    technical=ProviderTechnical(indicators=indicators) if not isinstance(indicators, Exception) and indicators else None,
                    news=news if not isinstance(news, Exception) else []
                )
        except Exception as e:
            logger.error(f"Error fetching from provider {type(provider).__name__} for {ticker}: {e}")

        # Final fallback: If preferred fails and it's not YFinance, try YFinance
        if preferred_source != "YFINANCE":
            yf_provider = ProviderFactory.get_provider(ticker, "YFINANCE")
            return await yf_provider.get_full_data(ticker)
            
        return None

    @staticmethod
    async def _update_database(ticker: str, data: FullMarketData, cache: Optional[MarketDataCache], db: AsyncSession, now: datetime):
        # Ensure Stock exists
        stock_stmt = select(Stock).where(Stock.ticker == ticker)
        stock_result = await db.execute(stock_stmt)
        stock = stock_result.scalar_one_or_none()
        
        if not stock:
            stock = Stock(ticker=ticker, name=data.quote.name or ticker)
            db.add(stock)
            await db.commit()
            # Refresh to get stock
            stock_result = await db.execute(stock_stmt)
            stock = stock_result.scalar_one_or_none()
        else:
            if data.quote.name:
                stock.name = data.quote.name

        # Update Stock Fundamentals
        fundamental = data.fundamental
        if fundamental:
            stock.sector = fundamental.sector or stock.sector
            stock.industry = fundamental.industry or stock.industry
            stock.market_cap = fundamental.market_cap or stock.market_cap
            stock.pe_ratio = fundamental.pe_ratio or stock.pe_ratio
            stock.forward_pe = fundamental.forward_pe or stock.forward_pe
            stock.eps = fundamental.eps or stock.eps
            stock.dividend_yield = fundamental.dividend_yield or stock.dividend_yield
            stock.beta = fundamental.beta or stock.beta
            stock.fifty_two_week_high = fundamental.fifty_two_week_high or stock.fifty_two_week_high
            stock.fifty_two_week_low = fundamental.fifty_two_week_low or stock.fifty_two_week_low

        # Update Cache
        if not cache:
            cache = MarketDataCache(ticker=ticker)
            db.add(cache)

        cache.current_price = data.quote.price
        cache.change_percent = data.quote.change_percent
        
        # Indicators
        if data.technical and data.technical.indicators:
            ind = data.technical.indicators
            cache.rsi_14 = ind.get('rsi_14', cache.rsi_14)
            cache.ma_20 = ind.get('ma_20', cache.ma_20)
            cache.ma_50 = ind.get('ma_50', cache.ma_50)
            cache.ma_200 = ind.get('ma_200', cache.ma_200)
            cache.macd_val = ind.get('macd_val', cache.macd_val)
            cache.macd_signal = ind.get('macd_signal', cache.macd_signal)
            cache.macd_hist = ind.get('macd_hist', cache.macd_hist)
            cache.bb_upper = ind.get('bb_upper', cache.bb_upper)
            cache.bb_middle = ind.get('bb_middle', cache.bb_middle)
            cache.bb_lower = ind.get('bb_lower', cache.bb_lower)
            cache.atr_14 = ind.get('atr_14', cache.atr_14)
            cache.k_line = ind.get('k_line', cache.k_line)
            cache.d_line = ind.get('d_line', cache.d_line)
            cache.j_line = ind.get('j_line', cache.j_line)
            cache.volume_ma_20 = ind.get('volume_ma_20', cache.volume_ma_20)
            cache.volume_ratio = ind.get('volume_ratio', cache.volume_ratio)

        cache.market_status = MarketStatus.OPEN
        cache.last_updated = now

        # Update News
        if data.news:
            from sqlalchemy.dialects.sqlite import insert
            for n in data.news:
                # Sanity check: need at least a link or it's not useful
                if not n.link:
                    continue
                
                news_stmt = insert(StockNews).values(
                    id=n.id or str(hash(n.link)),
                    ticker=ticker,
                    title=n.title or "No Title",
                    publisher=n.publisher or "Unknown",
                    link=n.link,
                    summary=n.summary,
                    publish_time=n.publish_time or now
                ).on_conflict_do_nothing()
                await db.execute(news_stmt)

        await db.commit()
        try:
            await db.refresh(cache)
        except Exception:
            pass
        return cache

    @staticmethod
    async def _handle_simulation(ticker: str, cache: Optional[MarketDataCache], now: datetime):
        import random
        if cache:
            fluctuation = 1 + (random.uniform(-0.0005, 0.0005))
            cache.current_price *= fluctuation
            cache.last_updated = now
            return cache
        
        # Mock Default
        return MarketDataCache(
            ticker=ticker,
            current_price=100.0 * (1 + random.uniform(-0.01, 0.01)),
            change_percent=random.uniform(-2.0, 2.0),
            last_updated=now,
            market_status=MarketStatus.OPEN
        )
