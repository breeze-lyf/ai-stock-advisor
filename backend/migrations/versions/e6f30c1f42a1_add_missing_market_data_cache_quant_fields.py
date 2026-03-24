"""add missing market_data_cache quant fields

Revision ID: e6f30c1f42a1
Revises: cfd52a8b3d1b
Create Date: 2026-03-24 12:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6f30c1f42a1"
down_revision: Union[str, Sequence[str], None] = "cfd52a8b3d1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _get_column_names("market_data_cache")
    with op.batch_alter_table("market_data_cache", schema=None) as batch_op:
        if "pe_percentile" not in columns:
            batch_op.add_column(sa.Column("pe_percentile", sa.Float(), nullable=True))
        if "pb_percentile" not in columns:
            batch_op.add_column(sa.Column("pb_percentile", sa.Float(), nullable=True))
        if "net_inflow" not in columns:
            batch_op.add_column(sa.Column("net_inflow", sa.Float(), nullable=True))


def downgrade() -> None:
    columns = _get_column_names("market_data_cache")
    with op.batch_alter_table("market_data_cache", schema=None) as batch_op:
        if "net_inflow" in columns:
            batch_op.drop_column("net_inflow")
        if "pb_percentile" in columns:
            batch_op.drop_column("pb_percentile")
        if "pe_percentile" in columns:
            batch_op.drop_column("pe_percentile")
