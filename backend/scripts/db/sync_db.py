import asyncio
import sys
import os
from pathlib import Path

# 确保能找到 app 模块
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.database import engine, Base
from app.models.notification import NotificationLog

async def sync_db():
    print("Connecting to database and creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database sync completed successfully.")

if __name__ == "__main__":
    asyncio.run(sync_db())
