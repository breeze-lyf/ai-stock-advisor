from __future__ import annotations

from sqlalchemy.engine import make_url


SSL_REQUIRED_VALUES = {"require", "verify-ca", "verify-full"}


def normalize_async_database_url(raw_url: str) -> str:
    """
    标准化数据库 URL 为 asyncpg 驱动格式。

    转换规则:
    - postgres:// → postgresql://
    - postgresql:// → postgresql+asyncpg:// (如未指定驱动)
    """
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)
    if raw_url.startswith("postgresql://") and "+asyncpg" not in raw_url:
        raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw_url


def build_postgres_connect_args(db_url: str) -> dict:
    """
    构建 PostgreSQL 连接参数，自动处理 SSL 配置。

    SSL 规则:
    - 本地 PostgreSQL (localhost/127.0.0.1): 禁用 SSL
    - 云端数据库 (Neon 等): 强制启用 SSL
    - 其他远程数据库：根据 sslmode 参数决定
    """
    parsed_url = make_url(db_url)
    host = (parsed_url.host or "").strip().lower()
    ssl_value = str(
        parsed_url.query.get("sslmode")
        or parsed_url.query.get("ssl")
        or ""
    ).strip().lower()
    is_local_postgres = host in {"127.0.0.1", "localhost"}

    # 云端数据库列表 (需要强制 SSL)
    CLOUD_DB_DOMAINS = {".neon.tech"}  # 可扩展其他云数据库域名

    is_cloud_db = any(host.endswith(domain) for domain in CLOUD_DB_DOMAINS)

    connect_args = {"command_timeout": 60}

    if ssl_value in SSL_REQUIRED_VALUES or is_cloud_db:
        connect_args["ssl"] = "require"
    elif is_local_postgres:
        connect_args["ssl"] = False

    return connect_args
