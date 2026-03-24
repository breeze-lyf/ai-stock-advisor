import asyncio
import pandas as pd
from app.services.market_providers.akshare import AkShareProvider
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_duplication():
    provider = AkShareProvider()
    symbols = ["AAPL", "NVDA", "000001.SZ", "600519.SH"]
    
    for symbol in symbols:
        logger.info(f"Testing {symbol}...")
        # 尝试不同来源
        df = await provider.get_ohlcv(symbol)
        if df:
            # 验证返回的列表是否唯一且有序
            times = [item.time for item in df]
            if len(times) != len(set(times)):
                logger.error(f"❌ Found duplicate timestamps in get_ohlcv output for {symbol}!")
            else:
                logger.info(f"✅ get_ohlcv output for {symbol} is clean.")
            
            # 验证顺序
            is_sorted = all(times[i] <= times[i+1] for i in range(len(times)-1))
            if not is_sorted:
                logger.error(f"❌ Timestamps in get_ohlcv output for {symbol} are NOT sorted!")
            else:
                logger.info(f"✅ Timestamps in get_ohlcv output for {symbol} are sorted.")

if __name__ == "__main__":
    asyncio.run(test_duplication())
