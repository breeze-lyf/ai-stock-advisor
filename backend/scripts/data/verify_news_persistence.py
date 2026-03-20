import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.database import SessionLocal, Base, engine
from app.services.macro_service import MacroService
from app.models.macro import GlobalNews, MacroTopic

async def verify():
    print("PHASE 1: Ensuring tables exist...")
    async with engine.begin() as conn:
        # 强制创建所有表，特别是新加的 global_news
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created/verified.")

    print("\nPHASE 2: Testing update_cls_news...")
    async with SessionLocal() as db:
        new_items = await MacroService.update_cls_news(db)
        print(f"Update finished. Created {len(new_items)} new items.")

    print("\nPHASE 3: Verifying database content...")
    async with SessionLocal() as db:
        all_news = await MacroService.get_latest_news(db)
        print(f"Total news items in DB: {len(all_news)}")
        for i, item in enumerate(all_news[:5]):
            print(f"[{i+1}] {item.published_at} | {item.title[:30]}...")

    print("\nVerification completed.")

if __name__ == "__main__":
    asyncio.run(verify())
