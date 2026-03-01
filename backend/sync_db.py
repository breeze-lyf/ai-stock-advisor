import asyncio
import sys
import os

# 确保能找到 app 模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import engine, Base
from app.models.notification import NotificationLog

async def sync_db():
    print("Connecting to database and creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database sync completed successfully.")

if __name__ == "__main__":
    asyncio.run(sync_db())
