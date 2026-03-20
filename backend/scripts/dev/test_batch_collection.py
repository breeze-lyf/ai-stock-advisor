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
from app.models.stock import MarketDataCache
from sqlalchemy.future import select

async def run_batch_test():
    print("🧪 [Batch Data Test] 启动本地小规模采集测试...")
    print("🎯 目标: 采集数据库中更新时间最老的 10 个数据 (yfinance)")
    
    async with SessionLocal() as db:
        try:
            # 1. 查找更新时间最老的 10 个缓存项
            # 排序：按照 last_updated 升序 (最老的前排)
            stmt = select(MarketDataCache).order_by(MarketDataCache.last_updated.asc()).limit(10)
            result = await db.execute(stmt)
            cache_items = result.scalars().all()
            
            if not cache_items:
                print("⚠️ 数据库中还没有股票缓存数据。尝试直接更新组合中的股票...")
                # 如果 cache 为空，尝试从 Portfolio 里抓取
                from app.models.portfolio import Portfolio
                stmt = select(Portfolio.ticker).distinct().limit(10)
                result = await db.execute(stmt)
                tickers = [row[0] for row in result.all()]
            else:
                tickers = [item.ticker for item in cache_items]

            if not tickers:
                print("❌ 没发现任何股票，请先在界面添加一些股票到自选。")
                return

            print(f"📋 选定采集目标: {tickers}")
            print("-" * 50)

            for ticker in tickers:
                start_time = time.time()
                print(f"🔍 正在采集: {ticker}...")
                
                try:
                    # 强制使用 YFINANCE 采集完整数据 (含基本面和技术面)
                    cache = await MarketDataService.get_real_time_data(ticker, db, preferred_source="YFINANCE")
                    
                    # 打印更新后的详细信息
                    duration = time.time() - start_time
                    print(f"✅ {ticker} 更新成功! (耗时: {duration:.2f}s)")
                    print(f"   💰 价格: ${cache.current_price:.2f} ({cache.change_percent:+.2f}%)")
                    print(f"   📊 趋势: RSI={cache.rsi_14:.2f}, MACD={cache.macd_val:.2f}, Hist={cache.macd_hist:.2f}")
                    print(f"   🌊 波动: BB=[{cache.bb_lower:.2f}, {cache.bb_middle:.2f}, {cache.bb_upper:.2f}], ATR={cache.atr_14:.2f}")
                    print(f"   🔍 震荡: KDJ=[K:{cache.k_line:.1f}, D:{cache.d_line:.1f}, J:{cache.j_line:.1f}]")
                    print(f"   📈 成交: Vol MA20={cache.volume_ma_20:.0f}, Ratio={cache.volume_ratio:.2f}")
                    
                    # 从 Stock 模型获取更新后的基本面 (由于 service 内部更新了 Stock)
                    from app.models.stock import Stock
                    stock_stmt = select(Stock).where(Stock.ticker == ticker)
                    stock_res = await db.execute(stock_stmt)
                    stock = stock_res.scalar_one()
                    
                    market_cap_display = f"{stock.market_cap / 1e9:.2f}B" if stock.market_cap else "N/A"
                    print(f"   🏢 基本面: 市值={market_cap_display}, PE={stock.pe_ratio or 'N/A'}, 行业={stock.industry or 'N/A'}")
                    print(f"   🕙 更新时间: {cache.last_updated}")
                
                except Exception as e:
                    print(f"❌ {ticker} 采集失败: {e}")

                print("-" * 30)
                # 稍微休息，防止瞬间请求过多
                await asyncio.sleep(2)

            print("\n🎉 测试采集任务完成！")

        except Exception as e:
            print(f"🔥 测试运行异常: {e}")

if __name__ == "__main__":
    asyncio.run(run_batch_test())
