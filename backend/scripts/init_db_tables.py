import asyncio
from app.core.database import engine, Base
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.stock import Stock, MarketDataCache

async def init_db():
    print("🚀 Initializing database...")
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())
