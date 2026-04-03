from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import event, text
from app.core.config import settings
from app.core.database_url import (
    build_postgres_connect_args,
    normalize_async_database_url,
)

# 数据库引擎核心配置 (Database Engine Config)

# 确保 URL 使用异步驱动 (Normalize DATABASE_URL)
db_url = normalize_async_database_url(settings.DATABASE_URL)

# PostgreSQL 连接配置
connect_args = build_postgres_connect_args(db_url)

# 连接池配置
# 本地 PostgreSQL / 自有 PostgreSQL 通用
engine = create_async_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=20,           # 连接池大小
    max_overflow=40,        # 最大溢出连接数
    pool_recycle=1800,      # 连接回收时间 (30 分钟)
    pool_timeout=30,        # 获取连接超时
    connect_args=connect_args
)

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
