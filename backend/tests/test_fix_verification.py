import asyncio
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.services.market_data import MarketDataService
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_fix():
    ticker = "600519"
    # 使用环境变量中的数据库连接字符串
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        logger.info(f"Triggering refresh for {ticker}...")
        # 强制刷新以触发抓取逻辑
        data = await MarketDataService.get_real_time_data(
            ticker=ticker, 
            db=db, 
            force_refresh=True,
            preferred_source="AKSHARE"
        )
        
        if data:
            logger.info(f"Refresh complete for {ticker}")
            logger.info(f"PE Percentile: {data.pe_percentile}")
            logger.info(f"PB Percentile: {data.pb_percentile}")
            logger.info(f"Net Inflow: {data.net_inflow}")
            logger.info(f"Last Updated: {data.last_updated}")
        else:
            logger.error("Failed to fetch data")

if __name__ == "__main__":
    asyncio.run(test_fix())
