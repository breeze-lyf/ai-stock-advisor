"""baseline

Revision ID: 35a834f440ba
Revises: 
Create Date: 2026-01-20 16:51:13.824633

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '35a834f440ba'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. 聪明地创建 PostgreSQL 枚举类型（如果不存在才创建）
    # 这样可以避免 "DuplicateObjectError"
    def create_type_if_not_exists(type_name, enum_values):
        values_str = ", ".join([f"'{v}'" for v in enum_values])
        op.execute(f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{type_name}') THEN CREATE TYPE {type_name} AS ENUM ({values_str}); END IF; END $$;")

    create_type_if_not_exists('membershiptier', ['FREE', 'PRO'])
    create_type_if_not_exists('marketdatasource', ['ALPHA_VANTAGE', 'YFINANCE'])
    create_type_if_not_exists('sentimentscore', ['BULLISH', 'BEARISH', 'NEUTRAL'])
    create_type_if_not_exists('marketstatus', ['PRE_MARKET', 'OPEN', 'AFTER_HOURS', 'CLOSED'])

    # 1. 创建 stocks 表
    op.create_table('stocks',
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('sector', sa.String(), nullable=True),
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('market_cap', sa.Float(), nullable=True),
        sa.Column('pe_ratio', sa.Float(), nullable=True),
        sa.Column('forward_pe', sa.Float(), nullable=True),
        sa.Column('eps', sa.Float(), nullable=True),
        sa.Column('dividend_yield', sa.Float(), nullable=True),
        sa.Column('beta', sa.Float(), nullable=True),
        sa.Column('fifty_two_week_high', sa.Float(), nullable=True),
        sa.Column('fifty_two_week_low', sa.Float(), nullable=True),
        sa.Column('exchange', sa.String(), nullable=True),
        sa.Column('currency', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('ticker')
    )
    op.create_index(op.f('ix_stocks_ticker'), 'stocks', ['ticker'], unique=False)

    # 2. 创建 users 表
    op.create_table('users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('membership_tier', sa.Enum('FREE', 'PRO', name='membershiptier', create_type=False), nullable=True),
        sa.Column('api_key_gemini', sa.String(), nullable=True),
        sa.Column('api_key_deepseek', sa.String(), nullable=True),
        sa.Column('preferred_data_source', sa.Enum('ALPHA_VANTAGE', 'YFINANCE', name='marketdatasource', create_type=False), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 3. 创建 market_data_cache 表
    op.create_table('market_data_cache',
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('current_price', sa.Float(), nullable=True),
        sa.Column('change_percent', sa.Float(), nullable=True),
        sa.Column('rsi_14', sa.Float(), nullable=True),
        sa.Column('ma_20', sa.Float(), nullable=True),
        sa.Column('ma_50', sa.Float(), nullable=True),
        sa.Column('ma_200', sa.Float(), nullable=True),
        sa.Column('market_status', sa.Enum('PRE_MARKET', 'OPEN', 'AFTER_HOURS', 'CLOSED', name='marketstatus', create_type=False), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ticker'], ['stocks.ticker'], ),
        sa.PrimaryKeyConstraint('ticker')
    )
    op.create_index(op.f('ix_market_data_cache_last_updated'), 'market_data_cache', ['last_updated'], unique=False)

    # 4. 创建 portfolios 表
    op.create_table('portfolios',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('ticker', sa.String(), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=True),
        sa.Column('avg_cost', sa.Float(), nullable=True),
        sa.Column('target_price', sa.Float(), nullable=True),
        sa.Column('stop_loss_price', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ticker'], ['stocks.ticker'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'ticker', name='unique_user_ticker')
    )

    # 5. 创建 stock_news 表
    op.create_table('stock_news',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('publisher', sa.String(), nullable=True),
        sa.Column('link', sa.String(), nullable=False),
        sa.Column('publish_time', sa.DateTime(), nullable=False),
        sa.Column('summary', sa.String(), nullable=True),
        sa.Column('sentiment', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['ticker'], ['stocks.ticker'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_news_ticker'), 'stock_news', ['ticker'], unique=False)

    # 6. 创建 analysis_reports 表
    op.create_table('analysis_reports',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('ticker', sa.String(), nullable=True),
        sa.Column('input_context_snapshot', sa.JSON(), nullable=True),
        sa.Column('ai_response_markdown', sa.Text(), nullable=True),
        sa.Column('sentiment_score', sa.Enum('BULLISH', 'BEARISH', 'NEUTRAL', name='sentimentscore', create_type=False), nullable=True),
        sa.Column('model_used', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ticker'], ['stocks.ticker'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analysis_reports_created_at'), 'analysis_reports', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
