
import asyncio
import os
import sys

# 动态添加项目根目录，确保能 import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, engine
from app.infrastructure.db.repositories.market_data_repository import MarketDataRepository
from app.schemas.market_data import FullMarketData, ProviderQuote, MarketStatus
from datetime import datetime

async def test_upsert_fix():
    print(f"Testing upsert fix with database: {engine.url}")
    async with SessionLocal() as db:
        repo = MarketDataRepository(db)
        ticker = "FIX_TEST_TICKER"
        
        # 准备数据，故意让 update_cols/update_set 逻辑导致空字典
        data = FullMarketData(
            quote=ProviderQuote(
                ticker=ticker,
                price=100.0,
                change_percent=2.0,
                name=ticker, # 这会让 _upsert_stock 的 update_cols 变为 {}
                last_updated=datetime.now(),
                market_status=MarketStatus.OPEN.value
            ),
            fundamental=None, # 没有基本面
            technical=None,  # 没有技术指标
            news=[]
        )
        
        now = datetime.now()
        try:
            # 第一次执行：插入数据
            print(f"Attempting first persist for {ticker}...")
            await repo.persist_market_data(ticker, data, None, now)
            print("First persist successful.")
            
            # 第二次执行：触发 upsert 逻辑，此时 update_cols 为空
            print(f"Attempting second persist for {ticker} (upsert with empty set)...")
            cache = await repo.get_market_cache(ticker)
            await repo.persist_market_data(ticker, data, cache, now)
            print("Second persist successful! Fix verified.")
            
        except Exception as e:
            print(f"❌ Fix failed or error occurred: {e}")
            import traceback
            traceback.print_exc()
            raise e
        finally:
            # 清理测试数据
            from sqlalchemy import text
            await db.execute(text("DELETE FROM market_data_cache WHERE ticker = :t"), {"t": ticker})
            await db.execute(text("DELETE FROM stocks WHERE ticker = :t"), {"t": ticker})
            await db.commit()
            print("Cleanup done.")

if __name__ == "__main__":
    asyncio.run(test_upsert_fix())
