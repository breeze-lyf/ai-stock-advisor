"""add users.price_color_mode (涨跌配色偏好，默认绿涨红跌)

Revision ID: f1c2d3e4a5b6
Revises: e8b2c3d4f5a6
"""
from alembic import op
import sqlalchemy as sa

revision = "f1c2d3e4a5b6"
down_revision = "e8b2c3d4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("price_color_mode", sa.String(), nullable=False, server_default="green_up"))


def downgrade() -> None:
    op.drop_column("users", "price_color_mode")
