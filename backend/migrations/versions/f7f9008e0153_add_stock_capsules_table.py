"""add_stock_capsules_table

Revision ID: f7f9008e0153
Revises: c0d1e2f3a4b5
Create Date: 2026-04-09 15:45:37.884369

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f7f9008e0153'
down_revision: Union[str, Sequence[str], None] = 'c0d1e2f3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create stock_capsules table."""
    op.create_table(
        'stock_capsules',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('capsule_type', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('source_count', sa.Integer(), nullable=True),
        sa.Column('model_used', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker', 'capsule_type', name='uq_stock_capsules_ticker_type'),
    )
    with op.batch_alter_table('stock_capsules', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_stock_capsules_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_stock_capsules_ticker'), ['ticker'], unique=False)


def downgrade() -> None:
    """Drop stock_capsules table."""
    with op.batch_alter_table('stock_capsules', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_stock_capsules_ticker'))
        batch_op.drop_index(batch_op.f('ix_stock_capsules_created_at'))
    op.drop_table('stock_capsules')
