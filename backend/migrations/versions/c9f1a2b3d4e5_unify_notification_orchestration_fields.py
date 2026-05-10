"""unify notification orchestration fields

Revision ID: c9f1a2b3d4e5
Revises: ab1cd2ef3456
Create Date: 2026-05-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9f1a2b3d4e5"
down_revision: Union[str, Sequence[str], None] = "ab1cd2ef3456"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("enable_indicator_alerts", sa.Boolean(), nullable=True, server_default=sa.text("true")))
        batch_op.add_column(sa.Column("enable_strategy_change_alerts", sa.Boolean(), nullable=True, server_default=sa.text("true")))

    op.execute("UPDATE users SET enable_indicator_alerts = true WHERE enable_indicator_alerts IS NULL")
    op.execute("UPDATE users SET enable_strategy_change_alerts = true WHERE enable_strategy_change_alerts IS NULL")

    with op.batch_alter_table("notification_logs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("target_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("semantic_key", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("priority", sa.String(), nullable=True))
        batch_op.create_index(batch_op.f("ix_notification_logs_target_id"), ["target_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_notification_logs_semantic_key"), ["semantic_key"], unique=False)
        batch_op.create_index(batch_op.f("ix_notification_logs_priority"), ["priority"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("notification_logs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_notification_logs_priority"))
        batch_op.drop_index(batch_op.f("ix_notification_logs_semantic_key"))
        batch_op.drop_index(batch_op.f("ix_notification_logs_target_id"))
        batch_op.drop_column("priority")
        batch_op.drop_column("semantic_key")
        batch_op.drop_column("target_id")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("enable_strategy_change_alerts")
        batch_op.drop_column("enable_indicator_alerts")
