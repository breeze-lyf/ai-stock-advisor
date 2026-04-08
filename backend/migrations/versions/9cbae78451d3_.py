"""empty message

Revision ID: 9cbae78451d3
Revises: 3c4d5e6f7a8b, a1b2c3d4e5f6, b1f6e6a7c2d4
Create Date: 2026-04-07 22:16:34.942182

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9cbae78451d3'
down_revision: Union[str, Sequence[str], None] = ('3c4d5e6f7a8b', 'a1b2c3d4e5f6', 'b1f6e6a7c2d4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
