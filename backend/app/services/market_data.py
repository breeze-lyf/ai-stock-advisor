import yfinance as yf
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
from app.models.stock import Stock, MarketDataCache, MarketStatus
import asyncio

class MarketDataService:
    @staticmethod
    async def get_real_time_data(ticker: str, db: AsyncSession):
        # 1. Check Cache
        stmt = select(MarketDataCache).where(MarketDataCache.ticker == ticker)
        result = await db.execute(stmt)
        cache = result.scalar_one_or_none()

        now = datetime.utcnow()
        if cache and (now - cache.last_updated) < timedelta(minutes=1):
            return cache

        # 2. Fetch from yfinance (Run in executor because yfinance is sync)
        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: MarketDataService._fetch_yfinance(ticker))
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            # Fallback for MVP if rate limited
            if not cache:
                return {
                    "shortName": ticker,
                    "currentPrice": 100.0,
                    "regularMarketPrice": 100.0,
                    "regularMarketChangePercent": 0.5,
                    "regularMarketOpen": 99.0,
                    "regularMarketDayHigh": 101.0,
                    "regularMarketDayLow": 99.0,
                    "volume": 1000000
                }
            return cache  # Return old cache if fetch fails

        # 3. Update/Create Cache
        if not cache:
            # Ensure Stock exists
            stock_stmt = select(Stock).where(Stock.ticker == ticker)
            stock_result = await db.execute(stock_stmt)
            stock = stock_result.scalar_one_or_none()
            
            if not stock:
                stock = Stock(ticker=ticker, name=data.get('shortName', ticker))
                db.add(stock)
                await db.commit() # Commit to ensure FK constraint met

            cache = MarketDataCache(ticker=ticker)
            db.add(cache)

        cache.current_price = data.get('currentPrice', data.get('regularMarketPrice'))
        cache.change_percent = data.get('regularMarketChangePercent')
        cache.market_status = MarketStatus.OPEN # simplified for now
        cache.last_updated = now
        
        # Add tech indicators placeholder (since pandas-ta is missing)
        cache.rsi_14 = 50.0 
        cache.ma_20 = cache.current_price
        cache.volume_ratio = 1.0

        await db.commit()
        await db.refresh(cache)
        return cache

    @staticmethod
    def _fetch_yfinance(ticker: str) -> dict:
        tick = yf.Ticker(ticker)
        # fast_info is often faster for real-time price
        info = tick.info
        # Use fast_info if available for fallback? 
        return info
