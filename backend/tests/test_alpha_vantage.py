import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add the project root to path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.services.market_data import MarketDataService
from app.core.database import Base

async def test_alpha_vantage_flow(ticker: str):
    print(f"--- Testing Alpha Vantage Flow for {ticker} ---")
    print(f"API Key present: {bool(settings.ALPHA_VANTAGE_API_KEY)}")
    
    # Setup temp DB session
    engine = create_async_engine(settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite+aiosqlite"))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # Force Alpha Vantage as preferred source
            print(f"Calling get_real_time_data with ALPHA_VANTAGE preference...")
            cache = await MarketDataService.get_real_time_data(ticker, db, preferred_source="ALPHA_VANTAGE")
            
            print("\n[SUCCESS] Data Retrieved and Cached:")
            print(f"Ticker: {cache.ticker}")
            print(f"Price: {cache.current_price}")
            print(f"Change %: {cache.change_percent}")
            print(f"Last Updated (UTC): {cache.last_updated}")
            
            # Check if fundamental data was also saved to Stock table
            from app.models.stock import Stock
            from sqlalchemy.future import select
            stmt = select(Stock).where(Stock.ticker == ticker)
            result = await db.execute(stmt)
            stock = result.scalar_one_or_none()
            
            if stock:
                print(f"\n[STOCK TABLE CHECK]:")
                print(f"Sector: {stock.sector}")
                print(f"Industry: {stock.industry}")
                print(f"Market Cap: {stock.market_cap}")
                print(f"PE Ratio: {stock.pe_ratio}")
                print(f"52W High: {stock.fifty_two_week_high}")
            
        except Exception as e:
            print(f"\n[ERROR]: {e}")
        finally:
            await engine.dispose()

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    asyncio.run(test_alpha_vantage_flow(ticker))
