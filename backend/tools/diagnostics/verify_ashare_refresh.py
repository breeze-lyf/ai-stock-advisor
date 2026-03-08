import asyncio
import os
import sys

# 将工程目录加入路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 明确清理环境，模拟无代理
for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy']:
    os.environ.pop(var, None)

from app.services.market_data import MarketDataService
from app.core.database import SessionLocal

async def verify():
    print("--- Verifying A-Share Refresh WITHOUT Proxy (Simulated) ---")
    async with SessionLocal() as db:
        # A股代码测试
        ticker = "002050"
        print(f"Fetching {ticker} (Price only mode)...")
        # 强制刷新以触发远程抓取
        cache = await MarketDataService.get_real_time_data(ticker, db, force_refresh=True, price_only=True)
        
        if cache:
            print(f"Success! {ticker} Price: {cache.current_price}")
            print(f"Change %: {cache.change_percent}%")
            print(f"Last Updated: {cache.last_updated}")
        else:
            print(f"Failed: No data returned for {ticker}.")

if __name__ == "__main__":
    asyncio.run(verify())
