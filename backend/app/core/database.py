from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import event, text
from app.core.config import settings

# 数据库引擎核心配置 (Database Engine Config)

# 判断是否为 PostgreSQL (Neon 等)
is_postgresql = "postgresql" in settings.DATABASE_URL

# 数据库引擎配置
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args = {
        "check_same_thread": False,
        "timeout": 30,
    }
elif is_postgresql:
    # Neon 强制要求 SSL
    connect_args = {
        "ssl": "require",
        "command_timeout": 60,
    }

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  
    pool_pre_ping=True,
    # PostgreSQL 连接池优化
    pool_size=10 if is_postgresql else 5,
    max_overflow=20 if is_postgresql else 0,
    pool_recycle=300,
    connect_args=connect_args
)

# --- SQLite WAL 核心模式 (上帝模式) ---
# 开启 WAL (预写日志) 模式。
# 这是 SQLite 性能翻倍的秘诀：它允许“读”和“写”同时进行，互不干扰。
if "sqlite" in settings.DATABASE_URL:
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")      # 开启读写并发
        cursor.execute("PRAGMA synchronous=NORMAL")   # 提升写入速度
        cursor.execute("PRAGMA busy_timeout=30000")   # 再次确保超时等待
        cursor.close()

# 会话工厂：它是生产数据库连接的“模具”
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False # 提交后不立即销毁对象，方便后续读取属性
)

# 声明基类：所有 Model 都要继承它，SQLAlchemy 才能通过它找到所有的表
Base = declarative_base()

# 依赖注入函数：用于 FastAPI 请求。
# 逻辑：请求进来时开门（创建 session），请求结束时关门（关闭 session）。
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback() # 出错时回滚，保护数据一致性
            raise
