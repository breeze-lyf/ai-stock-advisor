"""add_analyst_earnings_vix_fields

Add analyst coverage, earnings date, and VIX fields to stocks and market_data_cache tables.

Revision ID: b9e1f2a3c4d5
Revises: fe47ee3713dd
Create Date: 2026-04-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b9e1f2a3c4d5'
down_revision = 'fe47ee3713dd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- stocks table: analyst + earnings fields ---
    with op.batch_alter_table('stocks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('earnings_date', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('target_price_mean', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('analyst_count', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('analyst_buy_count', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('analyst_hold_count', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('analyst_sell_count', sa.Integer(), nullable=True))

    # --- market_data_cache table: VIX ---
    with op.batch_alter_table('market_data_cache', schema=None) as batch_op:
        batch_op.add_column(sa.Column('vix', sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('market_data_cache', schema=None) as batch_op:
        batch_op.drop_column('vix')

    with op.batch_alter_table('stocks', schema=None) as batch_op:
        batch_op.drop_column('analyst_sell_count')
        batch_op.drop_column('analyst_hold_count')
        batch_op.drop_column('analyst_buy_count')
        batch_op.drop_column('analyst_count')
        batch_op.drop_column('target_price_mean')
        batch_op.drop_column('earnings_date')
