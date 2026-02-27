import asyncio
from app.services.market_providers.akshare import AkShareProvider
from app.services.market_providers.factory import ProviderFactory

async def verify_a_shares():
    print("--- Verifying AkShareProvider for A-shares ---")
    provider = AkShareProvider()
    
    # Test 002050 (Sanhua)
    print("\nFetching 002050 (Sanhua) quote...")
    quote = await provider.get_quote("002050")
    if quote:
        print(f"Name: {quote.name}, Price: {quote.price}, Change%: {quote.change_percent}")
    else:
        print("Failed to fetch 002050 quote")

    # Test 600519 (Moutai)
    print("\nFetching 600519 (Moutai) quote...")
    quote = await provider.get_quote("600519")
    if quote:
        print(f"Name: {quote.name}, Price: {quote.price}, Change%: {quote.change_percent}")
    else:
        print("Failed to fetch 600519 quote")

    print("\n--- Verifying ProviderFactory Routing ---")
    tickers = ["002050", "600519", "AAPL", "002050.SZ", "600519.SS"]
    for t in tickers:
        p = ProviderFactory.get_provider(t)
        print(f"Ticker: {t:10} Provider: {type(p).__name__}")

if __name__ == "__main__":
    asyncio.run(verify_a_shares())
