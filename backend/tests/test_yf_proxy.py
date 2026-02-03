import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.market_data import MarketDataService
from app.core.config import settings
import asyncio

async def test_yf_proxy():
    print(f"Proxy Configured: {settings.HTTP_PROXY}")
    ticker = "AAPL"
    print(f"Testing yfinance for {ticker}...")
    
    try:
        # We manually call the static method for testing
        data = MarketDataService._fetch_yfinance(ticker)
        print("\n[SUCCESS] Data retrieved via yfinance:")
        print(f"Price: {data.get('price')}")
        print(f"Name: {data.get('shortName')}")
        print(f"Sector: {data.get('fundamental', {}).get('sector')}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n[FAILED] yfinance error: {e}")

if __name__ == "__main__":
    asyncio.run(test_yf_proxy())
