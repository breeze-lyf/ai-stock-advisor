import asyncio
import time
import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.database import SessionLocal, engine
from app.services.macro_service import MacroService
from app.models.macro import GlobalNews

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Diagnostic")

async def run_benchmark():
    print("=== PERFORMANCE BENCHMARK ===")
    
    # 1. Test AKShare Direct Fetch (Threaded)
    print("\n[1/3] Testing AKShare direct fetch (thread isolation)...")
    start = time.time()
    try:
        def fetch():
            import akshare as ak
            return ak.stock_info_global_cls()
        
        df = await asyncio.to_thread(fetch)
        end = time.time()
        print(f"AKShare Result: {'Success' if df is not None and not df.empty else 'Empty/Fail'}")
        print(f"AKShare Time: {end - start:.2f}s")
    except Exception as e:
        print(f"AKShare Error: {e}")

    # 2. Test Neon DB Query (Async)
    print("\n[2/3] Testing Neon DB query (GlobalNews)...")
    start = time.time()
    try:
        async with SessionLocal() as db:
            news = await MacroService.get_latest_news(db)
            end = time.time()
            print(f"DB Items Found: {len(news)}")
            print(f"DB Query Time: {end - start:.2f}s")
            if news:
                print(f"Latest News: {news[0].title[:50]}...")
    except Exception as e:
        print(f"DB Query Error: {e}")

    # 3. Test Full Service logic (Update + Persistence)
    print("\n[3/3] Testing Full Logic (Fetch -> Dedupe -> Save)...")
    start = time.time()
    try:
        async with SessionLocal() as db:
            new_items = await MacroService.update_cls_news(db)
            end = time.time()
            print(f"New Items Persisted: {len(new_items)}")
            print(f"Full Logic Time: {end - start:.2f}s")
    except Exception as e:
        print(f"Full Logic Error: {e}")

    print("\n=== BENCHMARK COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
