from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
import asyncio
import logging
from typing import Optional, Dict, Any

from app.core.config import settings
from app.models.stock import Stock, MarketDataCache, MarketStatus, StockNews
from app.services.market_providers import YFinanceProvider, AlphaVantageProvider

logger = logging.getLogger(__name__)

class MarketDataService:
    _providers = {
        "YFINANCE": YFinanceProvider(),
        "ALPHA_VANTAGE": AlphaVantageProvider()
    }

    @staticmethod
    async def get_real_time_data(ticker: str, db: AsyncSession, preferred_source: str = "ALPHA_VANTAGE", force_refresh: bool = False):
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
    async def _fetch_from_providers(ticker: str, preferred_source: str) -> Optional[Dict[str, Any]]:
        # Map of providers
        providers = MarketDataService._providers
        
        # Priority 1: Preferred Provider
        main_provider = providers.get(preferred_source)
        fallback_provider = providers.get("YFINANCE") if preferred_source != "YFINANCE" else providers.get("ALPHA_VANTAGE")
        
        result = None
        
        # Use a more efficient approach if it's YFinance
        if preferred_source == "YFINANCE" and main_provider:
            result = await main_provider.get_full_data(ticker)
            if result:
                return result

        # Otherwise, fetch components (potentially from multiple sources)
        if main_provider:
            try:
                # Parallel fetch Quote and Fundamentals from main
                quote_task = main_provider.get_quote(ticker)
                fundamental_task = main_provider.get_fundamental_data(ticker)
                
                # Fetch indicators and news from YFinance as it's more reliable/complete for free tier
                # If main is already YFinance we handled it above
                history_provider = providers.get("YFINANCE")
                indicator_task = history_provider.get_historical_data(ticker) if history_provider else asyncio.sleep(0, result=None)
                news_task = history_provider.get_news(ticker) if history_provider else asyncio.sleep(0, result=[])
                
                res = await asyncio.gather(quote_task, fundamental_task, indicator_task, news_task, return_exceptions=True)
                quote, fundamental, indicators, news = res
                
                if not isinstance(quote, Exception) and quote:
                    result = {
                        **quote,
                        "fundamental": fundamental if not isinstance(fundamental, Exception) and fundamental else {},
                        "indicators": indicators if not isinstance(indicators, Exception) and indicators else {},
                        "news": news if not isinstance(news, Exception) and news else []
                    }
                    return result
            except Exception as e:
                logger.error(f"Error fetching from preferred source {preferred_source}: {e}")

        # Final Fallback to YFinance for everything if we still have nothing
        if fallback_provider and preferred_source != "YFINANCE":
            if hasattr(fallback_provider, 'get_full_data'):
                return await fallback_provider.get_full_data(ticker)
            
        return None

    @staticmethod
    async def _update_database(ticker: str, data: Dict[str, Any], cache: Optional[MarketDataCache], db: AsyncSession, now: datetime):
        # Ensure Stock exists
        stock_stmt = select(Stock).where(Stock.ticker == ticker)
        stock_result = await db.execute(stock_stmt)
        stock = stock_result.scalar_one_or_none()
        
        if not stock:
            stock = Stock(ticker=ticker, name=data.get('name', ticker))
            db.add(stock)
            await db.commit()
            # Refresh to get stock
            stock_result = await db.execute(stock_stmt)
            stock = stock_result.scalar_one_or_none()

        # Update Stock Fundamentals
        fundamental = data.get('fundamental', {})
        if fundamental:
            stock.sector = fundamental.get('sector', stock.sector)
            stock.industry = fundamental.get('industry', stock.industry)
            stock.market_cap = fundamental.get('market_cap', stock.market_cap)
            stock.pe_ratio = fundamental.get('pe_ratio', stock.pe_ratio)
            stock.forward_pe = fundamental.get('forward_pe', stock.forward_pe)
            stock.eps = fundamental.get('eps', stock.eps)
            stock.dividend_yield = fundamental.get('dividend_yield', stock.dividend_yield)
            stock.beta = fundamental.get('beta', stock.beta)
            stock.fifty_two_week_high = fundamental.get('fifty_two_week_high', stock.fifty_two_week_high)
            stock.fifty_two_week_low = fundamental.get('fifty_two_week_low', stock.fifty_two_week_low)

        # Update Cache
        if not cache:
            cache = MarketDataCache(ticker=ticker)
            db.add(cache)

        cache.current_price = float(data.get('price', 0))
        cache.change_percent = float(data.get('change_percent', 0))
        
        # Indicators
        ind = data.get('indicators', {})
        if ind:
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
        news_list = data.get('news', [])
        if news_list:
            from sqlalchemy.dialects.sqlite import insert
            for n in news_list:
                news_stmt = insert(StockNews).values(
                    id=n.get('id'),
                    ticker=ticker,
                    title=n.get('title'),
                    publisher=n.get('publisher'),
                    link=n.get('link'),
                    publish_time=n.get('publish_time')
                ).on_conflict_do_nothing()
                await db.execute(news_stmt)

        await db.commit()
        try:
            await db.refresh(cache)
        except Exception:
            # Refresh might fail if item was just deleted or session issue
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
