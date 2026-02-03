import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.market_data import MarketDataService
from app.core.config import settings
import asyncio

async def test_av_proxy():
    print(f"Proxy Configured: {settings.HTTP_PROXY}")
    ticker = "AAPL"
    print(f"Testing Alpha Vantage for {ticker}...")
    
    try:
        data = MarketDataService._fetch_alpha_vantage(ticker)
        print("\n[SUCCESS] Data retrieved via Alpha Vantage:")
        print(f"Price: {data.get('price')}")
        print(f"Sector: {data.get('fundamental', {}).get('sector')}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n[FAILED] Alpha Vantage error: {e}")

if __name__ == "__main__":
    asyncio.run(test_av_proxy())
