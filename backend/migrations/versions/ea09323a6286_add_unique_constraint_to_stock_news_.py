"""Add unique constraint to stock_news ticker and link

Revision ID: ea09323a6286
Revises: 93320b786a9b
Create Date: 2026-02-19 12:22:23.856942

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ea09323a6286'
down_revision: Union[str, Sequence[str], None] = '93320b786a9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint('uq_stock_news_ticker_link', 'stock_news', ['ticker', 'link'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_stock_news_ticker_link', 'stock_news', type_='unique')
