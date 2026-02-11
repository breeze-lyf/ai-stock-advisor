from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import event, text
from app.core.config import settings

# SQLite 稳定性优化 (SQLite Stability Optimizations):
# 1. pool_size=5: 限制最大连接数，防止文件锁竞争
# 2. max_overflow=0: 不允许超出池大小的连接
# 3. pool_pre_ping=True: 每次使用连接前验证其有效性，防止使用已断开的连接
# 4. pool_recycle=300: 每 5 分钟回收连接，避免长时间持有过期连接
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # 关闭 SQL 日志以减少噪音（生产环境）
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=0,
    pool_recycle=300,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,  # SQLite busy timeout: 等待锁释放最多 30 秒
    } if "sqlite" in settings.DATABASE_URL else {}
)

# SQLite WAL 模式初始化 (Write-Ahead Logging)
# WAL 模式允许读写并发，极大减少 "database is locked" 错误
if "sqlite" in settings.DATABASE_URL:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

