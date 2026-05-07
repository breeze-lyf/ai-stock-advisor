"""add notification_logs table

Revision ID: ab1cd2ef3456
Revises: f7f9008e0153
Create Date: 2026-05-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ab1cd2ef3456'
down_revision: Union[str, None] = 'f7f9008e0153'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('notification_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('ticker', sa.String(), nullable=True),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('card_payload', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_logs_created_at'), 'notification_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_notification_logs_ticker'), 'notification_logs', ['ticker'], unique=False)
    op.create_index(op.f('ix_notification_logs_user_id'), 'notification_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_notification_logs_type'), 'notification_logs', ['type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notification_logs_type'), table_name='notification_logs')
    op.drop_index(op.f('ix_notification_logs_user_id'), table_name='notification_logs')
    op.drop_index(op.f('ix_notification_logs_ticker'), table_name='notification_logs')
    op.drop_index(op.f('ix_notification_logs_created_at'), table_name='notification_logs')
    op.drop_table('notification_logs')
