import asyncio
import sys
import os
from datetime import datetime
import time
import random
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.database import SessionLocal
from app.services.market_data import MarketDataService
from app.models.portfolio import Portfolio
from sqlalchemy.future import select

async def run_collector():
    print("🚀 [数据采集器] 启动...")
    print("⏰ 策略: 低频采集 (每分钟 1 次) 以保护 IP 安全")
    
    while True:
        async with SessionLocal() as db:
            try:
                # 1. 获取所有在用户组合中的股票代码 (去重)
                stmt = select(Portfolio.ticker).distinct()
                result = await db.execute(stmt)
                tickers = [row[0] for row in result.all()]
                
                if not tickers:
                    print("📝 组合中暂无股票，等待 60 秒...")
                    await asyncio.sleep(60)
                    continue

                print(f"📊 发现 {len(tickers)} 只股票需要维护: {tickers}")

                for ticker in tickers:
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"🔄 [{now_str}] 正在抓取: {ticker}...")
                    
                    try:
                        # 强制使用 YFINANCE 获取并更新持久层 (Stock 和 MarketDataCache)
                        # get_real_time_data 内部已经处理了 Stock 和 Cache 的保存逻辑
                        await MarketDataService.get_real_time_data(ticker, db, preferred_source="YFINANCE")
                        print(f"✅ {ticker} 数据已持久化。")
                    except Exception as e:
                        print(f"❌ {ticker} 抓取失败: {e}")

                    # ⏳ 核心保护逻辑：每抓完一只，强制休息 60 秒
                    # 这样一小时只发 60 个请求，绝对触发不了雅虎的限流
                    wait_time = 60 + random.uniform(0, 5) 
                    print(f"🛡️ 保护 IP 中... 随机休眠 {wait_time:.1f} 秒...")
                    await asyncio.sleep(wait_time)

            except Exception as e:
                print(f"🔥 采集器循环异常: {e}")
                await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(run_collector())
    except KeyboardInterrupt:
        print("\n👋 采集器已停止。")
