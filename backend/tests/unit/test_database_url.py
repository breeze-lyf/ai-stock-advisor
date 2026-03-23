from app.core.database_url import (
    build_postgres_connect_args,
    normalize_async_database_url,
)


def test_normalize_postgres_scheme_to_asyncpg():
    url = "postgres://user:pass@db.example.com:5432/app"
    assert normalize_async_database_url(url) == "postgresql+asyncpg://user:pass@db.example.com:5432/app"


def test_preserve_asyncpg_url():
    url = "postgresql+asyncpg://user:pass@db.example.com:5432/app?ssl=require"
    assert normalize_async_database_url(url) == url


def test_require_ssl_when_ssl_query_alias_is_present():
    url = "postgresql+asyncpg://user:pass@db.example.com:5432/app?ssl=require"
    assert build_postgres_connect_args(url)["ssl"] == "require"


def test_disable_ssl_for_local_postgres():
    url = "postgresql+asyncpg://user:pass@127.0.0.1:5432/app"
    assert build_postgres_connect_args(url)["ssl"] is False
