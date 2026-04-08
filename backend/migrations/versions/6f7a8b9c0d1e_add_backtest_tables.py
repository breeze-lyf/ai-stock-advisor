"""add_backtest_tables

Revision ID: 6f7a8b9c0d1e
Revises: 5e6f7a8b9c0d
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f7a8b9c0d1e'
down_revision: Union[str, None] = '5e6f7a8b9c0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建回测配置表
    op.create_table(
        'backtest_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('strategy_type', sa.String(length=50), nullable=False),
        sa.Column('tickers', sa.String(length=500), nullable=True),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('market', sa.String(length=10), nullable=True),
        sa.Column('entry_conditions', sa.JSON(), nullable=True),
        sa.Column('exit_conditions', sa.JSON(), nullable=True),
        sa.Column('position_size_pct', sa.Numeric(5, 2), nullable=False, default=20.0),
        sa.Column('max_positions', sa.Integer(), nullable=False, default=5),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('initial_capital', sa.Numeric(12, 2), nullable=False, default=1000000),
        sa.Column('commission_rate', sa.Numeric(8, 6), nullable=False, default=0.0003),
        sa.Column('slippage_pct', sa.Numeric(5, 4), nullable=False, default=0.001),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backtest_configs_user_id'), 'backtest_configs', ['user_id'], unique=False)

    # 创建回测结果表
    op.create_table(
        'backtest_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('config_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, default='PENDING'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('execution_time_seconds', sa.Numeric(10, 2), nullable=True),
        sa.Column('total_return', sa.Numeric(10, 4), nullable=True),
        sa.Column('annualized_return', sa.Numeric(10, 4), nullable=True),
        sa.Column('benchmark_return', sa.Numeric(10, 4), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(10, 4), nullable=True),
        sa.Column('max_drawdown_duration_days', sa.Integer(), nullable=True),
        sa.Column('volatility', sa.Numeric(10, 4), nullable=True),
        sa.Column('downside_deviation', sa.Numeric(10, 4), nullable=True),
        sa.Column('sharpe_ratio', sa.Numeric(6, 4), nullable=True),
        sa.Column('sortino_ratio', sa.Numeric(6, 4), nullable=True),
        sa.Column('calmar_ratio', sa.Numeric(6, 4), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=True),
        sa.Column('winning_trades', sa.Integer(), nullable=True),
        sa.Column('losing_trades', sa.Integer(), nullable=True),
        sa.Column('win_rate', sa.Numeric(6, 4), nullable=True),
        sa.Column('avg_win_pct', sa.Numeric(8, 4), nullable=True),
        sa.Column('avg_loss_pct', sa.Numeric(8, 4), nullable=True),
        sa.Column('profit_factor', sa.Numeric(6, 4), nullable=True),
        sa.Column('avg_holding_period_days', sa.Numeric(6, 2), nullable=True),
        sa.Column('final_capital', sa.Numeric(14, 2), nullable=True),
        sa.Column('total_commission', sa.Numeric(12, 2), nullable=True),
        sa.Column('equity_curve', sa.JSON(), nullable=True),
        sa.Column('trades', sa.JSON(), nullable=True),
        sa.Column('monthly_returns', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backtest_results_config_id'), 'backtest_results', ['config_id'], unique=False)
    op.create_index(op.f('ix_backtest_results_user_id'), 'backtest_results', ['user_id'], unique=False)

    # 创建预设策略表
    op.create_table(
        'saved_strategies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('entry_conditions', sa.JSON(), nullable=False),
        sa.Column('exit_conditions', sa.JSON(), nullable=False),
        sa.Column('default_position_size', sa.Numeric(5, 2), nullable=False, default=20.0),
        sa.Column('applicable_markets', sa.String(length=50), nullable=True),
        sa.Column('applicable_sectors', sa.String(length=200), nullable=True),
        sa.Column('historical_return_1y', sa.Numeric(8, 4), nullable=True),
        sa.Column('historical_sharpe', sa.Numeric(6, 4), nullable=True),
        sa.Column('historical_max_drawdown', sa.Numeric(8, 4), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 添加外键约束
    op.create_foreign_key(
        'fk_backtest_configs_user',
        'backtest_configs',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_backtest_results_config',
        'backtest_results',
        'backtest_configs',
        ['config_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_backtest_results_user',
        'backtest_results',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # 删除外键约束
    op.drop_constraint('fk_backtest_results_user', 'backtest_results', type_='foreignkey')
    op.drop_constraint('fk_backtest_results_config', 'backtest_results', type_='foreignkey')
    op.drop_constraint('fk_backtest_configs_user', 'backtest_configs', type_='foreignkey')

    # 删除索引
    op.drop_index(op.f('ix_backtest_results_user_id'), table_name='backtest_results')
    op.drop_index(op.f('ix_backtest_results_config_id'), table_name='backtest_results')
    op.drop_index(op.f('ix_backtest_configs_user_id'), table_name='backtest_configs')

    # 删除表
    op.drop_table('saved_strategies')
    op.drop_table('backtest_results')
    op.drop_table('backtest_configs')
