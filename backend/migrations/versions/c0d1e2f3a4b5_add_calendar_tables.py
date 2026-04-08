"""add_calendar_tables

Revision ID: c0d1e2f3a4b5
Revises: b9e1f2a3c4d5
Create Date: 2026-04-09 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c0d1e2f3a4b5'
down_revision: Union[str, None] = 'b9e1f2a3c4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'economic_events',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('event_time', sa.String(20), nullable=True),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC'),
        sa.Column('country', sa.String(50), nullable=False),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('importance', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('forecast', sa.Float(), nullable=True),
        sa.Column('previous', sa.Float(), nullable=True),
        sa.Column('actual', sa.Float(), nullable=True),
        sa.Column('impact_analysis', sa.Text(), nullable=True),
        sa.Column('affected_sectors', sa.Text(), nullable=True),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_pushed', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_economic_events_event_date', 'economic_events', ['event_date'])
    op.create_index('ix_economic_events_event_type', 'economic_events', ['event_type'])

    op.create_table(
        'earnings_events',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(20), nullable=False),
        sa.Column('company_name', sa.String(200), nullable=False),
        sa.Column('report_type', sa.String(20), nullable=False),
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('fiscal_quarter', sa.Integer(), nullable=True),
        sa.Column('report_date', sa.Date(), nullable=False),
        sa.Column('report_time', sa.String(20), nullable=True),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='America/New_York'),
        sa.Column('eps_estimate', sa.Float(), nullable=True),
        sa.Column('eps_actual', sa.Float(), nullable=True),
        sa.Column('revenue_estimate', sa.Float(), nullable=True),
        sa.Column('revenue_actual', sa.Float(), nullable=True),
        sa.Column('market_reaction', sa.Text(), nullable=True),
        sa.Column('analyst_commentary', sa.Text(), nullable=True),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_pushed', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_earnings_events_ticker', 'earnings_events', ['ticker'])
    op.create_index('ix_earnings_events_report_date', 'earnings_events', ['report_date'])

    op.create_table(
        'user_calendar_alerts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('event_id', sa.String(), nullable=True),
        sa.Column('ticker', sa.String(20), nullable=True),
        sa.Column('country', sa.String(50), nullable=True),
        sa.Column('importance_min', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('remind_before_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_calendar_alerts_user_id', 'user_calendar_alerts', ['user_id'])


def downgrade() -> None:
    op.drop_table('user_calendar_alerts')
    op.drop_table('earnings_events')
    op.drop_table('economic_events')
