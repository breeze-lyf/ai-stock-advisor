"""add missing user preferences and macro tables

Revision ID: f5f8d8c2b1aa
Revises: e6f30c1f42a1
Create Date: 2026-03-24 15:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f5f8d8c2b1aa"
down_revision: Union[str, Sequence[str], None] = "e6f30c1f42a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_table_names() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _get_column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _get_index_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    table_names = _get_table_names()
    user_columns = _get_column_names("users")

    with op.batch_alter_table("users", schema=None) as batch_op:
        if "timezone" not in user_columns:
            batch_op.add_column(sa.Column("timezone", sa.String(), nullable=True, server_default="Asia/Shanghai"))
        if "theme" not in user_columns:
            batch_op.add_column(sa.Column("theme", sa.String(), nullable=True, server_default="light"))
        if "feishu_webhook_url" not in user_columns:
            batch_op.add_column(sa.Column("feishu_webhook_url", sa.String(), nullable=True))

    op.execute("UPDATE users SET timezone = 'Asia/Shanghai' WHERE timezone IS NULL")
    op.execute("UPDATE users SET theme = 'light' WHERE theme IS NULL")

    if "macro_topics" not in table_names:
        op.create_table(
            "macro_topics",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("heat_score", sa.Float(), nullable=True),
            sa.Column("impact_analysis", sa.JSON(), nullable=True),
            sa.Column("source_links", sa.JSON(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if "global_news" not in table_names:
        op.create_table(
            "global_news",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("published_at", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("fingerprint", sa.String(), nullable=True),
            sa.Column("is_headline", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if "global_news" in _get_table_names():
        global_news_indexes = _get_index_names("global_news")
        if "ix_global_news_fingerprint" not in global_news_indexes:
            op.create_index("ix_global_news_fingerprint", "global_news", ["fingerprint"], unique=True)

    if "global_hourly_reports" not in _get_table_names():
        op.create_table(
            "global_hourly_reports",
            sa.Column("hour_key", sa.String(), nullable=False),
            sa.Column("core_summary", sa.Text(), nullable=False),
            sa.Column("impact_map", sa.JSON(), nullable=True),
            sa.Column("sentiment", sa.String(), nullable=True),
            sa.Column("news_count", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("hour_key"),
        )


def downgrade() -> None:
    table_names = _get_table_names()

    if "global_hourly_reports" in table_names:
        op.drop_table("global_hourly_reports")

    if "global_news" in table_names:
        global_news_indexes = _get_index_names("global_news")
        if "ix_global_news_fingerprint" in global_news_indexes:
            op.drop_index("ix_global_news_fingerprint", table_name="global_news")
        op.drop_table("global_news")

    if "macro_topics" in table_names:
        op.drop_table("macro_topics")

    user_columns = _get_column_names("users")
    with op.batch_alter_table("users", schema=None) as batch_op:
        if "feishu_webhook_url" in user_columns:
            batch_op.drop_column("feishu_webhook_url")
        if "theme" in user_columns:
            batch_op.drop_column("theme")
        if "timezone" in user_columns:
            batch_op.drop_column("timezone")
