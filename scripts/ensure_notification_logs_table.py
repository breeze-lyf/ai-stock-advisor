import asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

async def ensure_notification_logs_table():
    engine = create_async_engine("postgresql+asyncpg://ai_stock_app:KfZpdJdl7PsVlEJfij7oBZLb@host.docker.internal:5432/ai_stock_advisor")
    async with engine.begin() as conn:
        await conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS notification_logs (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR,
                ticker VARCHAR,
                type VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                content TEXT,
                card_payload JSON,
                status VARCHAR DEFAULT 'SUCCESS',
                created_at TIMESTAMP
            )
        """))
        for col, idx_name in [("created_at", "ix_notification_logs_created_at"), ("ticker", "ix_notification_logs_ticker"), ("user_id", "ix_notification_logs_user_id"), ("type", "ix_notification_logs_type")]:
            await conn.execute(sa.text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON notification_logs ({col})"))
    print("notification_logs table ensured")
    await engine.dispose()

asyncio.run(ensure_notification_logs_table())
