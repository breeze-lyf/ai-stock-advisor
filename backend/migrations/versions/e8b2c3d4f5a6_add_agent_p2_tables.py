"""agent P2: daily briefs, notifier configs, advice records

Revision ID: e8b2c3d4f5a6
Revises: d7a1b2c3e4f5
"""
from alembic import op
import sqlalchemy as sa

revision = "e8b2c3d4f5a6"
down_revision = "d7a1b2c3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_daily_briefs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brief_date", sa.String(10), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tickers", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("pushed_channels", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "brief_date", name="uq_agent_brief_user_date"),
    )
    op.create_index("ix_agent_daily_briefs_user_id", "agent_daily_briefs", ["user_id"])
    op.create_table(
        "agent_notifier_configs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("secret", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("brief_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_status", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_agent_notifier_configs_user_id", "agent_notifier_configs", ["user_id"])
    op.create_table(
        "agent_advice_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("price_at", sa.Float(), nullable=True),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("target_price", sa.Float(), nullable=True),
        sa.Column("stop_loss", sa.Float(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("conversation_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=False),
        sa.Column("eval_price", sa.Float(), nullable=True),
        sa.Column("return_pct", sa.Float(), nullable=True),
        sa.Column("hit", sa.Boolean(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    for col in ("user_id", "ticker", "status", "due_at"):
        op.create_index(f"ix_agent_advice_records_{col}", "agent_advice_records", [col])


def downgrade() -> None:
    op.drop_table("agent_advice_records")
    op.drop_table("agent_notifier_configs")
    op.drop_table("agent_daily_briefs")
