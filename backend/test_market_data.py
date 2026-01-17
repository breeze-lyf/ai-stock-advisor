import asyncio
import sys
import os

# Create a new event loop policy (fixes RuntimeError on Windows, good practice generally for scripts)
# asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()) 

sys.path.append(os.getcwd())

from app.core.database import SessionLocal, engine
from app.services.market_data import MarketDataService

async def main():
    async with SessionLocal() as session:
        print("Fetching NVDA data...")
        data = await MarketDataService.get_real_time_data("NVDA", session)
        print(f"Ticker: {data.ticker}")
        print(f"Price: {data.current_price}")
        print(f"Last Updated: {data.last_updated}")
        
        print("\nFetching again (should catch cache)...")
        data2 = await MarketDataService.get_real_time_data("NVDA", session)
        print(f"Last Updated: {data2.last_updated}")

if __name__ == "__main__":
    asyncio.run(main())
