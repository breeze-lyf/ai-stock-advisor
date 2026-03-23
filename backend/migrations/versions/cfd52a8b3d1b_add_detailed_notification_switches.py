"""add_detailed_notification_switches_and_restore_tables

Revision ID: cfd52a8b3d1b
Revises: 3e8869343958
Create Date: 2026-03-23 15:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cfd52a8b3d1b'
down_revision: Union[str, Sequence[str], None] = '3e8869343958'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # 1. Add missing notification columns to users
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('enable_price_alerts', sa.Boolean(), nullable=True, server_default=sa.text('true')))
        batch_op.add_column(sa.Column('enable_hourly_summary', sa.Boolean(), nullable=True, server_default=sa.text('true')))
        batch_op.add_column(sa.Column('enable_daily_report', sa.Boolean(), nullable=True, server_default=sa.text('true')))
        batch_op.add_column(sa.Column('enable_macro_alerts', sa.Boolean(), nullable=True, server_default=sa.text('true')))

    # Update existing rows to True
    op.execute("UPDATE users SET enable_price_alerts = true WHERE enable_price_alerts IS NULL")
    op.execute("UPDATE users SET enable_hourly_summary = true WHERE enable_hourly_summary IS NULL")
    op.execute("UPDATE users SET enable_daily_report = true WHERE enable_daily_report IS NULL")
    op.execute("UPDATE users SET enable_macro_alerts = true WHERE enable_macro_alerts IS NULL")

    # 2. Restore missing tables
    if 'simulated_trades' not in tables:
        # Check if tradestatus enum exists in Postgres
        if bind.dialect.name == 'postgresql':
            # Create the type if it doesn't exist
            op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tradestatus') THEN CREATE TYPE tradestatus AS ENUM ('OPEN', 'CLOSED_PROFIT', 'CLOSED_LOSS', 'CLOSED_MANUAL'); END IF; END $$;")
            trade_status_enum = postgresql.ENUM('OPEN', 'CLOSED_PROFIT', 'CLOSED_LOSS', 'CLOSED_MANUAL', name='tradestatus', create_type=False)
        else:
            trade_status_enum = sa.Enum('OPEN', 'CLOSED_PROFIT', 'CLOSED_LOSS', 'CLOSED_MANUAL', name='tradestatus')

        op.create_table('simulated_trades',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('ticker', sa.String(), nullable=False),
            sa.Column('status', trade_status_enum, nullable=False),
            sa.Column('entry_date', sa.DateTime(), nullable=False),
            sa.Column('entry_price', sa.Float(), nullable=False),
            sa.Column('entry_reason', sa.Text(), nullable=True),
            sa.Column('target_price', sa.Float(), nullable=True),
            sa.Column('stop_loss_price', sa.Float(), nullable=True),
            sa.Column('current_price', sa.Float(), nullable=True),
            sa.Column('unrealized_pnl_pct', sa.Float(), nullable=True),
            sa.Column('exit_date', sa.DateTime(), nullable=True),
            sa.Column('exit_price', sa.Float(), nullable=True),
            sa.Column('realized_pnl_pct', sa.Float(), nullable=True),
            sa.Column('exit_reason', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['ticker'], ['stocks.ticker'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('simulated_trades', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_simulated_trades_status'), ['status'], unique=False)
            batch_op.create_index(batch_op.f('ix_simulated_trades_ticker'), ['ticker'], unique=False)
            batch_op.create_index(batch_op.f('ix_simulated_trades_user_id'), ['user_id'], unique=False)

    if 'trade_history_logs' not in tables:
        op.create_table('trade_history_logs',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('trade_id', sa.String(), nullable=False),
            sa.Column('log_date', sa.DateTime(), nullable=False),
            sa.Column('price', sa.Float(), nullable=False),
            sa.Column('pnl_pct', sa.Float(), nullable=False),
            sa.ForeignKeyConstraint(['trade_id'], ['simulated_trades.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('trade_history_logs', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_trade_history_logs_trade_id'), ['trade_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('enable_macro_alerts')
        batch_op.drop_column('enable_daily_report')
        batch_op.drop_column('enable_hourly_summary')
        batch_op.drop_column('enable_price_alerts')
    
    op.drop_table('trade_history_logs')
    op.drop_table('simulated_trades')
