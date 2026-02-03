import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import sys
import os

# Try to connect to the DB as the app would
db_url = "sqlite+aiosqlite:///./ai_advisor.db"

async def test_conn():
    print(f"Testing connection to {db_url}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"File exists: {os.path.exists('ai_advisor.db')}")
    
    try:
        engine = create_async_engine(db_url)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = result.fetchall()
            print(f"Connected! Tables found: {[t[0] for t in tables]}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_conn())
