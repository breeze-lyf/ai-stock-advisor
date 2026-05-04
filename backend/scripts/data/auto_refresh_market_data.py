import asyncio
import logging
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.database import SessionLocal
from app.services.market_data import MarketDataService
from app.models.stock import Stock, MarketDataCache
from sqlalchemy.future import select
from app.utils.json_logger import setup_logging

# Use the project's logging setup (with rotation)
setup_logging(
    log_format="text",
    log_level="INFO",
    service_name="auto-refresh-worker",
    environment="development",
    log_file=str(Path(__file__).resolve().parents[1] / ".local" / "runtime-logs" / "auto_refresh.log"),
    max_bytes=10 * 1024 * 1024,
    backup_count=3,
)
logger = logging.getLogger(__name__)

async def auto_refresh_job():
    """Background job to refresh the stalest stock data every 5 minutes."""
    logger.info("Starting auto-refresh background job...")

    while True:
        try:
            async with SessionLocal() as db:
                stmt = select(Stock.ticker).outerjoin(
                    MarketDataCache, Stock.ticker == MarketDataCache.ticker
                ).order_by(
                    MarketDataCache.last_updated.asc().nullsfirst()
                ).limit(10)

                result = await db.execute(stmt)
                tickers = result.scalars().all()

            if tickers:
                logger.info(f"Refreshing stalest {len(tickers)} stocks: {', '.join(tickers)}...")
                for ticker in tickers:
                    async with SessionLocal() as db:
                        try:
                            updated_cache = await MarketDataService.get_real_time_data(ticker, db, force_refresh=True)
                            if updated_cache:
                                logger.info(f"Successfully refreshed {ticker}. New Price: {updated_cache.current_price}")
                            else:
                                logger.warning(f"Failed to refresh data for {ticker}.")
                        except Exception as fetch_error:
                            logger.error(f"Error fetching data for {ticker}: {fetch_error}")

                    await asyncio.sleep(2)
            else:
                logger.info("No stocks found in database to refresh.")

        except Exception as e:
            logger.error(f"Critical error in auto-refresh loop: {e}")

        await asyncio.sleep(300)

if __name__ == "__main__":
    try:
        asyncio.run(auto_refresh_job())
    except KeyboardInterrupt:
        logger.info("Auto-refresh job stopped by user.")
