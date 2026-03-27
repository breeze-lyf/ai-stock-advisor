import asyncio
import os
import sys

# 将项目根目录添加到 python 路径，确保在容器中运行脚本时能正确导入 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import engine
from app.core.database_url import normalize_async_database_url


def mask_database_url(raw_url: str) -> str:
    if "@" not in raw_url or "://" not in raw_url:
        return raw_url
    scheme, rest = raw_url.split("://", 1)
    _, host_part = rest.split("@", 1)
    return f"{scheme}://****:****@{host_part}"


async def main() -> int:
    normalized_url = normalize_async_database_url(settings.DATABASE_URL)
    print(f"Preflight DATABASE_URL: {mask_database_url(normalized_url)}")

    max_retries = 5
    retry_interval = 5

    try:
        for attempt in range(1, max_retries + 1):
            try:
                print(f"Database preflight check attempt {attempt}/{max_retries}...")
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                print("Database preflight check passed.")
                return 0
            except Exception as exc:
                message = str(exc)
                print(f"Attempt {attempt} failed: {type(exc).__name__}: {message}")
                if attempt < max_retries:
                    print(f"Retrying in {retry_interval} seconds...")
                    await asyncio.sleep(retry_interval)
                    continue

                if "compute time quota" in message.lower():
                    print("Detected Neon compute quota exhaustion. Resume or upgrade the Neon project before deployment.")
                elif "password authentication failed" in message.lower():
                    print("Detected PostgreSQL authentication failure. Verify DATABASE_URL credentials on the server.")
                elif "temporary failure in name resolution" in message.lower() or "name or service not known" in message.lower():
                    print("Detected database DNS resolution failure. Verify the database hostname and outbound network access.")
                elif isinstance(exc, SQLAlchemyError):
                    print("Detected SQLAlchemy connectivity failure. Verify DATABASE_URL scheme, SSL mode, and database availability.")
                return 1
    finally:
        await engine.dispose()
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
