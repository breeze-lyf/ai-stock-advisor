from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import event, text
from app.core.config import settings

# 数据库引擎核心配置 (Database Engine Config)
# 职责：建立 Python 与数据库之间的“高速公路”。
# 本项目采用异步 (Async) 驱动，保证在抓取行情等耗时操作时，不会堵塞其他用户的请求。

# SQLite 稳定性专项优化：
# 由于 SQLite 本质是一个文件，高并发时容易出现 "database is locked"（数据库被锁住）。
# 我们通过下述配置极大缓解这个问题：
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  
    pool_pre_ping=True, # 每次拿连接前先“踢一脚”，确保它是活的
    pool_size=5,        # 限制并发连接数，防止排队太长
    max_overflow=0,
    pool_recycle=300,   # 每 5 分钟重置连接，保持新鲜
    connect_args={
        "check_same_thread": False,
        "timeout": 30,  # 如果数据库被锁，最多耐心等 30 秒，而不是直接报错
    } if "sqlite" in settings.DATABASE_URL else {}
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
