
import asyncio
import logging
import sys
import os

# Ensure backend directory is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from app.services.market_data import MarketDataService
from app.models.stock import Stock, MarketDataCache
from sqlalchemy.future import select

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def auto_refresh_job():
    """
    Background job to refresh the stalest stock data every 5 minutes.
    """
    logger.info("🚀 Starting auto-refresh background job...")
    
    while True:
        async with SessionLocal() as db:
            try:
                # Query to find the stock with the oldest update time (or NULL if never updated)
                # Logic: Left Join Stock -> MarketDataCache, Order by last_updated ASC NULLS FIRST
                stmt = select(Stock.ticker).outerjoin(
                    MarketDataCache, Stock.ticker == MarketDataCache.ticker
                ).order_by(
                    MarketDataCache.last_updated.asc().nullsfirst()
                ).limit(10)
                
                result = await db.execute(stmt)
                tickers = result.scalars().all()
                
                if tickers:
                    logger.info(f"🔄 Refreshing stalest {len(tickers)} stocks: {', '.join(tickers)}...")
                    for ticker in tickers:
                        try:
                            updated_cache = await MarketDataService.get_real_time_data(ticker, db, force_refresh=True)
                            if updated_cache:
                                logger.info(f"✅ Successfully refreshed {ticker}. New Price: {updated_cache.current_price}")
                            else:
                                logger.warning(f"⚠️ Failed to refresh data for {ticker}.")
                        except Exception as fetch_error:
                            logger.error(f"❌ Error fetching data for {ticker}: {fetch_error}")
                        
                        # 休眠 2 秒，避免短时间内突然发出大量请求导致 IP 被封
                        await asyncio.sleep(2)
                else:
                    logger.info("ℹ️ No stocks found in database to refresh.")
                    
            except Exception as e:
                logger.error(f"💥 Critical error in auto-refresh loop: {e}")
        
        # Sleep for 5 minutes (300 seconds)
        logger.info("💤 Sleeping for 5 minutes...")
        await asyncio.sleep(300)

if __name__ == "__main__":
    try:
        asyncio.run(auto_refresh_job())
    except KeyboardInterrupt:
        logger.info("🛑 Auto-refresh job stopped by user.")
