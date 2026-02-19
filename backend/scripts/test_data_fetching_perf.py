
import asyncio
import time
import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.market_providers import ProviderFactory
from app.schemas.market_data import FullMarketData
from app.core.database import SessionLocal

# Setup logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataFetchTest")

TEST_STOCKS = {
    "US": ["AAPL", "TSLA", "AMD"],
    "CN": ["002050", "600519", "002970"]
}

REQUIRED_CACHE_FIELDS = [
    "current_price", "change_percent", "rsi_14", "ma_20", "ma_50", "ma_200", 
    "macd_val", "macd_signal", "macd_hist", "bb_upper", "bb_middle", "bb_lower", 
    "atr_14", "volume_ratio"
]

REQUIRED_STOCK_FIELDS = [
    "name", "sector", "market_cap", "pe_ratio", "eps"
]

async def test_single_stock(ticker: str, source: str):
    logger.info(f"== Testing {ticker} via {source} ==")
    provider = ProviderFactory.get_provider(ticker, source)
    
    results = {}
    
    # 1. Test Quote
    start = time.time()
    quote = await provider.get_quote(ticker)
    results['quote_time'] = time.time() - start
    results['quote_success'] = quote is not None
    
    # 2. Test Fundamental
    start = time.time()
    fundamental = await provider.get_fundamental_data(ticker)
    results['fundamental_time'] = time.time() - start
    results['fundamental_success'] = fundamental is not None
    
    # 3. Test Historical/Indicators
    start = time.time()
    indicators = await provider.get_historical_data(ticker, period="200d")
    results['indicator_time'] = time.time() - start
    results['indicator_success'] = indicators is not None
    
    # 4. Test News
    start = time.time()
    news = await provider.get_news(ticker)
    results['news_time'] = time.time() - start
    results['news_success'] = len(news) > 0

    # Fields Check
    missing_fields = []
    
    if quote:
        for f in ["price", "change_percent", "name"]:
            if getattr(quote, f, None) is None:
                missing_fields.append(f"quote.{f}")
    else:
        missing_fields.append("quote.*")

    if fundamental:
        for f in REQUIRED_STOCK_FIELDS:
            if getattr(fundamental, f, None) is None:
                missing_fields.append(f"fundamental.{f}")
    else:
        missing_fields.append("fundamental.*")

    if indicators:
        for f in REQUIRED_CACHE_FIELDS:
            # Note: handle mapping from calculate_all result keys to required fields
            match_key = f
            if f == "current_price": continue # calculated from quote
            if f == "change_percent": continue # calculated from quote
            
            # map schema names to internal calc keys if different
            calc_key = f
            if f == "macd_val": calc_key = "macd_val"
            
            if indicators.get(calc_key) is None:
                missing_fields.append(f"indicator.{f}")
    else:
        missing_fields.append("indicators.*")

    results['missing_fields'] = missing_fields
    
    logger.info(f"Stock: {ticker} | Total Time Est: {results['quote_time'] + results['fundamental_time'] + results['indicator_time']:.2f}s")
    logger.info(f"Success: Quote({results['quote_success']}), Fund({results['fundamental_success']}), Ind({results['indicator_success']}), News({results['news_success']})")
    if missing_fields:
        logger.warning(f"Missing Fields: {', '.join(missing_fields)}")
    
    return results

async def main():
    final_report = []
    
    # Test US
    for ticker in TEST_STOCKS["US"]:
        res = await test_single_stock(ticker, "YFINANCE")
        res['ticker'] = ticker
        res['market'] = "US"
        final_report.append(res)
        
    # Test CN
    for ticker in TEST_STOCKS["CN"]:
        res = await test_single_stock(ticker, "AKSHARE")
        res['ticker'] = ticker
        res['market'] = "CN"
        final_report.append(res)
        
    # Summary Table
    print("\n" + "="*80)
    print(f"{'Ticker':<10} | {'Market':<6} | {'Quote(s)':<8} | {'Fund(s)':<8} | {'Ind(s)':<8} | {'News':<5} | {'Missing Fields'}")
    print("-" * 80)
    for r in final_report:
        print(f"{r['ticker']:<10} | {r['market']:<6} | {r['quote_time']:<8.2f} | {r['fundamental_time']:<8.2f} | {r['indicator_time']:<8.2f} | {str(r['news_success']):<5} | {', '.join(r['missing_fields'][:3])}{'...' if len(r['missing_fields'])>3 else ''}")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
