import asyncio
from app.core.database import engine
from sqlalchemy import text

async def add_index():
    print("🚀 Adding index to portfolios(user_id)...")
    async with engine.begin() as conn:
        try:
            # SQLite specific index creation
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_portfolios_user_id ON portfolios (user_id)"))
            print("✅ Index added successfully!")
        except Exception as e:
            print(f"❌ Failed to add index: {e}")

if __name__ == "__main__":
    asyncio.run(add_index())
