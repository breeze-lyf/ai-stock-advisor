import asyncio
import os
import sys
from pathlib import Path

# 将工程目录加入路径
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

# 模拟无代理环境
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('all_proxy', None)

from app.services.market_data import MarketDataService
from app.core.database import SessionLocal

async def verify():
    print("--- Verifying US Stock Fetching WITHOUT Proxy (Simulated) ---")
    async with SessionLocal() as db:
        ticker = "AAPL"
        # 强制刷新以触发远程抓取
        cache = await MarketDataService.get_real_time_data(ticker, db, force_refresh=True)
        
        if cache:
            print(f"Success! {ticker} Price: {cache.current_price}")
            print(f"Last Updated: {cache.last_updated}")
            if cache.last_updated.year == 2000:
                print("Bad: System entered simulation mode.")
            else:
                print("Good: Real data fetched from fallback source.")
        else:
            print("Failed: No data returned.")

if __name__ == "__main__":
    asyncio.run(verify())
