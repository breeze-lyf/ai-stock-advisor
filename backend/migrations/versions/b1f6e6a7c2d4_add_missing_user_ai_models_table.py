"""add missing user ai models table

Revision ID: b1f6e6a7c2d4
Revises: 9c3dd2fb5d2a
Create Date: 2026-03-24 16:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1f6e6a7c2d4"
down_revision: Union[str, Sequence[str], None] = "9c3dd2fb5d2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_table_names() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _get_index_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    table_names = _get_table_names()

    if "user_ai_models" not in table_names:
        op.create_table(
            "user_ai_models",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("key", sa.String(), nullable=False),
            sa.Column("display_name", sa.String(), nullable=False),
            sa.Column("provider_note", sa.String(), nullable=True),
            sa.Column("model_id", sa.String(), nullable=False),
            sa.Column("encrypted_api_key", sa.String(), nullable=True),
            sa.Column("base_url", sa.String(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "key", name="uq_user_ai_models_user_key"),
        )

    if "user_ai_models" in _get_table_names():
        index_names = _get_index_names("user_ai_models")
        if "ix_user_ai_models_user_id" not in index_names:
            op.create_index("ix_user_ai_models_user_id", "user_ai_models", ["user_id"], unique=False)
        if "ix_user_ai_models_key" not in index_names:
            op.create_index("ix_user_ai_models_key", "user_ai_models", ["key"], unique=False)


def downgrade() -> None:
    table_names = _get_table_names()
    if "user_ai_models" in table_names:
        index_names = _get_index_names("user_ai_models")
        if "ix_user_ai_models_key" in index_names:
            op.drop_index("ix_user_ai_models_key", table_name="user_ai_models")
        if "ix_user_ai_models_user_id" in index_names:
            op.drop_index("ix_user_ai_models_user_id", table_name="user_ai_models")
        op.drop_table("user_ai_models")
