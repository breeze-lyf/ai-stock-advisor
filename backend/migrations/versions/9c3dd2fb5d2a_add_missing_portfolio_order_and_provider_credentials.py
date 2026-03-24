"""add missing portfolio order and provider credentials

Revision ID: 9c3dd2fb5d2a
Revises: f5f8d8c2b1aa
Create Date: 2026-03-24 16:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c3dd2fb5d2a"
down_revision: Union[str, Sequence[str], None] = "f5f8d8c2b1aa"
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

    portfolio_columns = _get_column_names("portfolios")
    with op.batch_alter_table("portfolios", schema=None) as batch_op:
        if "sort_order" not in portfolio_columns:
            batch_op.add_column(sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"))

    op.execute("UPDATE portfolios SET sort_order = 0 WHERE sort_order IS NULL")

    if "user_provider_credentials" not in table_names:
        op.create_table(
            "user_provider_credentials",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("provider_key", sa.String(), nullable=False),
            sa.Column("encrypted_api_key", sa.String(), nullable=True),
            sa.Column("base_url", sa.String(), nullable=True),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "provider_key", name="uq_user_provider_credentials_user_provider"),
        )

    if "user_provider_credentials" in _get_table_names():
        index_names = _get_index_names("user_provider_credentials")
        if "ix_user_provider_credentials_user_id" not in index_names:
            op.create_index("ix_user_provider_credentials_user_id", "user_provider_credentials", ["user_id"], unique=False)
        if "ix_user_provider_credentials_provider_key" not in index_names:
            op.create_index("ix_user_provider_credentials_provider_key", "user_provider_credentials", ["provider_key"], unique=False)


def downgrade() -> None:
    table_names = _get_table_names()

    if "user_provider_credentials" in table_names:
        index_names = _get_index_names("user_provider_credentials")
        if "ix_user_provider_credentials_provider_key" in index_names:
            op.drop_index("ix_user_provider_credentials_provider_key", table_name="user_provider_credentials")
        if "ix_user_provider_credentials_user_id" in index_names:
            op.drop_index("ix_user_provider_credentials_user_id", table_name="user_provider_credentials")
        op.drop_table("user_provider_credentials")

    portfolio_columns = _get_column_names("portfolios")
    with op.batch_alter_table("portfolios", schema=None) as batch_op:
        if "sort_order" in portfolio_columns:
            batch_op.drop_column("sort_order")
