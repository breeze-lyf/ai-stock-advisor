
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath("backend"))

from app.models.stock import MarketDataCache

async def check_rklb():
    engine = create_async_engine("sqlite+aiosqlite:///backend/ai_advisor.db")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        stmt = select(MarketDataCache).where(MarketDataCache.ticker == 'RKLB')
        result = await session.execute(stmt)
        cache = result.scalar_one_or_none()
        
        if cache:
            print(f"Ticker: {cache.ticker}")
            print(f"Price: {cache.current_price}")
            print(f"RSI: {cache.rsi_14}")
            print(f"MACD: {cache.macd_val} (Hist: {cache.macd_hist})")
            print(f"Bollinger: [{cache.bb_lower}, {cache.bb_upper}]")
            print(f"MA: [20: {cache.ma_20}, 50: {cache.ma_50}, 200: {cache.ma_200}]")
        else:
            print("No cache found for RKLB")

if __name__ == "__main__":
    asyncio.run(check_rklb())
