"""add_quant_factor_tables

Revision ID: b2c3d4e5f6a1
Revises: 8b9c0d1e2f3a
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a1'
down_revision: Union[str, None] = '8b9c0d1e2f3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建量化因子定义表
    op.create_table(
        'quant_factors',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code_name', sa.String(length=50), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('formula', sa.Text(), nullable=True),
        sa.Column('calculation_params', sa.JSON(), nullable=True),
        sa.Column('lookback_period', sa.Integer(), nullable=False, default=252),
        sa.Column('decay_period', sa.Integer(), nullable=False, default=0),
        sa.Column('data_source', sa.String(length=50), nullable=False, default='market_data'),
        sa.Column('frequency', sa.String(length=20), nullable=False, default='DAILY'),
        sa.Column('ic_mean', sa.Numeric(8, 6), nullable=True),
        sa.Column('ic_ir', sa.Numeric(8, 4), nullable=True),
        sa.Column('rank_ic_mean', sa.Numeric(8, 6), nullable=True),
        sa.Column('rank_ic_ir', sa.Numeric(8, 4), nullable=True),
        sa.Column('annual_return', sa.Numeric(8, 4), nullable=True),
        sa.Column('sharpe_ratio', sa.Numeric(8, 4), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(8, 4), nullable=True),
        sa.Column('win_rate', sa.Numeric(6, 4), nullable=True),
        sa.Column('turnover_rate', sa.Numeric(8, 4), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_custom', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('code_name'),
    )

    # 创建因子值表
    op.create_table(
        'quant_factor_values',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('factor_id', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('trade_date', sa.DateTime(), nullable=False),
        sa.Column('value', sa.Numeric(18, 8), nullable=True),
        sa.Column('zscore_value', sa.Numeric(10, 4), nullable=True),
        sa.Column('rank_value', sa.Numeric(6, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['factor_id'], ['quant_factors.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_quant_factor_values_factor_id', 'quant_factor_values', ['factor_id'])
    op.create_index('ix_quant_factor_values_ticker', 'quant_factor_values', ['ticker'])
    op.create_index('ix_quant_factor_values_trade_date', 'quant_factor_values', ['trade_date'])
    op.create_unique_constraint(
        'uq_factor_ticker_date',
        'quant_factor_values',
        ['factor_id', 'ticker', 'trade_date']
    )

    # 创建量化策略表
    op.create_table(
        'quant_strategies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('strategy_type', sa.String(length=50), nullable=False),
        sa.Column('factor_weights', sa.JSON(), nullable=True),
        sa.Column('rebalance_frequency', sa.String(length=20), nullable=False, default='WEEKLY'),
        sa.Column('max_position_pct', sa.Numeric(5, 2), nullable=False, default=10.0),
        sa.Column('max_sector_exposure', sa.Numeric(5, 2), nullable=False, default=30.0),
        sa.Column('min_market_cap', sa.Numeric(18, 2), nullable=True),
        sa.Column('max_stocks', sa.Integer(), nullable=False, default=50),
        sa.Column('turnover_limit', sa.Numeric(5, 2), nullable=False, default=50.0),
        sa.Column('stop_loss_pct', sa.Numeric(5, 2), nullable=False, default=10.0),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_backtesting', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_quant_strategies_user_id', 'quant_strategies', ['user_id'])

    # 创建量化信号表
    op.create_table(
        'quant_signals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('signal_date', sa.DateTime(), nullable=False),
        sa.Column('signal_strength', sa.Numeric(6, 4), nullable=False, default=0.0),
        sa.Column('target_weight', sa.Numeric(6, 4), nullable=True),
        sa.Column('current_price', sa.Numeric(18, 4), nullable=True),
        sa.Column('factor_scores', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='PENDING'),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('executed_price', sa.Numeric(18, 4), nullable=True),
        sa.Column('executed_volume', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['strategy_id'], ['quant_strategies.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_quant_signals_strategy_id', 'quant_signals', ['strategy_id'])
    op.create_index('ix_quant_signals_ticker', 'quant_signals', ['ticker'])
    op.create_index('ix_quant_signals_signal_date', 'quant_signals', ['signal_date'])

    # 创建回测结果表
    op.create_table(
        'quant_backtest_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('factor_id', sa.String(), nullable=True),
        sa.Column('strategy_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('backtest_name', sa.String(length=200), nullable=False),
        sa.Column('backtest_start', sa.DateTime(), nullable=False),
        sa.Column('backtest_end', sa.DateTime(), nullable=False),
        sa.Column('initial_capital', sa.Numeric(14, 2), nullable=False, default=1000000),
        sa.Column('commission_rate', sa.Numeric(8, 6), nullable=False, default=0.0003),
        sa.Column('slippage_rate', sa.Numeric(8, 6), nullable=False, default=0.001),
        sa.Column('backtest_params', sa.JSON(), nullable=True),
        sa.Column('total_return', sa.Numeric(10, 4), nullable=False, default=0.0),
        sa.Column('annual_return', sa.Numeric(10, 4), nullable=False, default=0.0),
        sa.Column('benchmark_return', sa.Numeric(10, 4), nullable=True),
        sa.Column('excess_return', sa.Numeric(10, 4), nullable=True),
        sa.Column('sharpe_ratio', sa.Numeric(8, 4), nullable=True),
        sa.Column('sortino_ratio', sa.Numeric(8, 4), nullable=True),
        sa.Column('calmar_ratio', sa.Numeric(8, 4), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(10, 4), nullable=True),
        sa.Column('max_drawdown_duration_days', sa.Integer(), nullable=True),
        sa.Column('volatility', sa.Numeric(10, 4), nullable=True),
        sa.Column('beta', sa.Numeric(8, 4), nullable=True),
        sa.Column('alpha', sa.Numeric(10, 4), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=False, default=0),
        sa.Column('winning_trades', sa.Integer(), nullable=False, default=0),
        sa.Column('losing_trades', sa.Integer(), nullable=False, default=0),
        sa.Column('win_rate', sa.Numeric(6, 4), nullable=True),
        sa.Column('avg_win_pct', sa.Numeric(8, 4), nullable=True),
        sa.Column('avg_loss_pct', sa.Numeric(8, 4), nullable=True),
        sa.Column('profit_factor', sa.Numeric(8, 4), nullable=True),
        sa.Column('avg_holding_days', sa.Numeric(6, 2), nullable=True),
        sa.Column('turnover_rate', sa.Numeric(8, 4), nullable=True),
        sa.Column('ic_mean', sa.Numeric(8, 6), nullable=True),
        sa.Column('ic_ir', sa.Numeric(8, 4), nullable=True),
        sa.Column('rank_ic_mean', sa.Numeric(8, 6), nullable=True),
        sa.Column('rank_ic_ir', sa.Numeric(8, 4), nullable=True),
        sa.Column('final_capital', sa.Numeric(14, 2), nullable=False, default=0.0),
        sa.Column('total_commission', sa.Numeric(12, 2), nullable=True),
        sa.Column('equity_curve', sa.JSON(), nullable=True),
        sa.Column('positions_history', sa.JSON(), nullable=True),
        sa.Column('trades', sa.JSON(), nullable=True),
        sa.Column('monthly_returns', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='COMPLETED'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['factor_id'], ['quant_factors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['strategy_id'], ['quant_strategies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_quant_backtest_results_factor_id', 'quant_backtest_results', ['factor_id'])
    op.create_index('ix_quant_backtest_results_strategy_id', 'quant_backtest_results', ['strategy_id'])
    op.create_index('ix_quant_backtest_results_user_id', 'quant_backtest_results', ['user_id'])

    # 创建因子 IC 历史表
    op.create_table(
        'factor_ic_history',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('factor_id', sa.String(), nullable=False),
        sa.Column('stat_date', sa.DateTime(), nullable=False),
        sa.Column('stat_period', sa.String(length=20), nullable=False, default='DAILY'),
        sa.Column('ic', sa.Numeric(8, 6), nullable=True),
        sa.Column('rank_ic', sa.Numeric(8, 6), nullable=True),
        sa.Column('long_return', sa.Numeric(10, 4), nullable=True),
        sa.Column('short_return', sa.Numeric(10, 4), nullable=True),
        sa.Column('long_short_return', sa.Numeric(10, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['factor_id'], ['quant_factors.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_factor_ic_history_factor_id', 'factor_ic_history', ['factor_id'])
    op.create_index('ix_factor_ic_history_stat_date', 'factor_ic_history', ['stat_date'])

    # 创建组合优化配置表
    op.create_table(
        'quant_optimization_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('optimizer_type', sa.String(length=50), nullable=False),
        sa.Column('risk_aversion', sa.Numeric(4, 2), nullable=True),
        sa.Column('target_return', sa.Numeric(6, 4), nullable=True),
        sa.Column('target_volatility', sa.Numeric(6, 4), nullable=True),
        sa.Column('max_weight', sa.Numeric(5, 2), nullable=False, default=10.0),
        sa.Column('min_weight', sa.Numeric(5, 2), nullable=False, default=0.0),
        sa.Column('sector_constraints', sa.JSON(), nullable=True),
        sa.Column('max_turnover', sa.Numeric(5, 2), nullable=True),
        sa.Column('benchmark_tracking_error', sa.Numeric(6, 4), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_quant_optimization_configs_user_id', 'quant_optimization_configs', ['user_id'])


def downgrade() -> None:
    op.drop_table('quant_optimization_configs')
    op.drop_table('factor_ic_history')
    op.drop_table('quant_backtest_results')
    op.drop_table('quant_signals')
    op.drop_table('quant_strategies')
    op.drop_table('quant_factor_values')
    op.drop_table('quant_factors')
