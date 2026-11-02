"""add agent conversations, messages and personal API tokens

Revision ID: d7a1b2c3e4f5
Revises: c9f1a2b3d4e5
Create Date: 2026-11-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7a1b2c3e4f5"
down_revision: Union[str, Sequence[str], None] = "c9f1a2b3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_conversations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="web"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_agent_conversations_user_id", "agent_conversations", ["user_id"])

    op.create_table(
        "agent_messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("conversation_id", sa.String(), sa.ForeignKey("agent_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("tool_trace", sa.Text(), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_agent_messages_conversation_id", "agent_messages", ["conversation_id"])
    op.create_index("ix_agent_messages_created_at", "agent_messages", ["created_at"])

    op.create_table(
        "user_api_tokens",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False, server_default="MCP"),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_prefix", sa.String(length=16), nullable=False),
        sa.Column("scopes", sa.String(length=200), nullable=False, server_default="agent:read"),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_api_tokens_user_id", "user_api_tokens", ["user_id"])
    op.create_index("ix_user_api_tokens_token_hash", "user_api_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_api_tokens_token_hash", table_name="user_api_tokens")
    op.drop_index("ix_user_api_tokens_user_id", table_name="user_api_tokens")
    op.drop_table("user_api_tokens")
    op.drop_index("ix_agent_messages_created_at", table_name="agent_messages")
    op.drop_index("ix_agent_messages_conversation_id", table_name="agent_messages")
    op.drop_table("agent_messages")
    op.drop_index("ix_agent_conversations_user_id", table_name="agent_conversations")
    op.drop_table("agent_conversations")
