"""add data source config fields to users

Revision ID: a1b2c3d4e5f6
Revises: f5f8d8c2b1aa
Create Date: 2026-04-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f5f8d8c2b1aa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加分市场数据源配置字段
    op.add_column(
        'users',
        sa.Column('data_source_a_share', sa.String(), nullable=True, default='YFINANCE')
    )
    op.add_column(
        'users',
        sa.Column('data_source_hk_share', sa.String(), nullable=True, default='YFINANCE')
    )
    op.add_column(
        'users',
        sa.Column('data_source_us_share', sa.String(), nullable=True, default='YFINANCE')
    )

    # 更新默认值为 YFINANCE
    op.execute("UPDATE users SET data_source_a_share = 'YFINANCE' WHERE data_source_a_share IS NULL")
    op.execute("UPDATE users SET data_source_hk_share = 'YFINANCE' WHERE data_source_hk_share IS NULL")
    op.execute("UPDATE users SET data_source_us_share = 'YFINANCE' WHERE data_source_us_share IS NULL")

    # 设置为非空
    op.alter_column('users', 'data_source_a_share', existing_type=sa.String(), nullable=False)
    op.alter_column('users', 'data_source_hk_share', existing_type=sa.String(), nullable=False)
    op.alter_column('users', 'data_source_us_share', existing_type=sa.String(), nullable=False)


def downgrade() -> None:
    op.drop_column('users', 'data_source_us_share')
    op.drop_column('users', 'data_source_hk_share')
    op.drop_column('users', 'data_source_a_share')
