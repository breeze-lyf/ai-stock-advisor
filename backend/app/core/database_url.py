from __future__ import annotations

from sqlalchemy.engine import make_url


SSL_REQUIRED_VALUES = {"require", "verify-ca", "verify-full"}


def normalize_async_database_url(raw_url: str) -> str:
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)
    if raw_url.startswith("postgresql://") and "+asyncpg" not in raw_url:
        raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw_url


def build_postgres_connect_args(db_url: str) -> dict:
    parsed_url = make_url(db_url)
    host = (parsed_url.host or "").strip().lower()
    ssl_value = str(
        parsed_url.query.get("sslmode")
        or parsed_url.query.get("ssl")
        or ""
    ).strip().lower()
    is_local_postgres = host in {"127.0.0.1", "localhost"}
    is_neon = host.endswith(".neon.tech")

    connect_args = {"command_timeout": 60}
    if ssl_value in SSL_REQUIRED_VALUES or is_neon:
        connect_args["ssl"] = "require"
    elif is_local_postgres:
        connect_args["ssl"] = False

    return connect_args
