"""add_ai_signal_history_tables

Revision ID: 4d5e6f7a8b9c
Revises: 9cbae78451d3
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d5e6f7a8b9c'
down_revision: Union[str, None] = '9cbae78451d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 AI 信号历史表
    op.create_table(
        'ai_signal_history',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('signal_type', sa.Enum('BUY', 'SELL', 'HOLD', 'STRONG_BUY', 'STRONG_SELL', name='signaltype'), nullable=False),
        sa.Column('signal_status', sa.Enum('ACTIVE', 'CLOSED', 'EXPIRED', 'CANCELLED', name='signalstatus'), nullable=False, default='ACTIVE'),
        sa.Column('entry_price', sa.Numeric(12, 4), nullable=False),
        sa.Column('target_price', sa.Numeric(12, 4), nullable=True),
        sa.Column('stop_loss_price', sa.Numeric(12, 4), nullable=True),
        sa.Column('confidence_score', sa.Integer(), nullable=False, default=50),
        sa.Column('time_horizon', sa.String(length=20), nullable=False, default='SHORT'),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('key_factors', sa.Text(), nullable=True),
        sa.Column('exit_price', sa.Numeric(12, 4), nullable=True),
        sa.Column('exit_reason', sa.String(length=50), nullable=True),
        sa.Column('pnl_percent', sa.Numeric(10, 4), nullable=True),
        sa.Column('pnl_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(10, 4), nullable=True),
        sa.Column('max_gain', sa.Numeric(10, 4), nullable=True),
        sa.Column('analysis_report_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_signal_history_user_id'), 'ai_signal_history', ['user_id'], unique=False)
    op.create_index(op.f('ix_ai_signal_history_ticker'), 'ai_signal_history', ['ticker'], unique=False)

    # 创建 AI 信号表现统计表
    op.create_table(
        'ai_signal_performance',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('period', sa.String(length=20), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('total_signals', sa.Integer(), nullable=False, default=0),
        sa.Column('closed_signals', sa.Integer(), nullable=False, default=0),
        sa.Column('winning_signals', sa.Integer(), nullable=False, default=0),
        sa.Column('losing_signals', sa.Integer(), nullable=False, default=0),
        sa.Column('win_rate', sa.Numeric(6, 4), nullable=False, default=0),
        sa.Column('avg_pnl_percent', sa.Numeric(10, 4), nullable=False, default=0),
        sa.Column('avg_gain_percent', sa.Numeric(10, 4), nullable=False, default=0),
        sa.Column('avg_loss_percent', sa.Numeric(10, 4), nullable=False, default=0),
        sa.Column('profit_factor', sa.Numeric(6, 4), nullable=False, default=0),
        sa.Column('best_signal_ticker', sa.String(length=20), nullable=True),
        sa.Column('best_signal_pnl', sa.Numeric(10, 4), nullable=True),
        sa.Column('worst_signal_ticker', sa.String(length=20), nullable=True),
        sa.Column('worst_signal_pnl', sa.Numeric(10, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_signal_performance_user_id'), 'ai_signal_performance', ['user_id'], unique=False)

    # 添加外键约束
    op.create_foreign_key(
        'fk_ai_signal_history_user',
        'ai_signal_history',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_ai_signal_history_analysis_report',
        'ai_signal_history',
        'analysis_reports',
        ['analysis_report_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_ai_signal_performance_user',
        'ai_signal_performance',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # 删除外键约束
    op.drop_constraint('fk_ai_signal_performance_user', 'ai_signal_performance', type_='foreignkey')
    op.drop_constraint('fk_ai_signal_history_analysis_report', 'ai_signal_history', type_='foreignkey')
    op.drop_constraint('fk_ai_signal_history_user', 'ai_signal_history', type_='foreignkey')

    # 删除索引
    op.drop_index(op.f('ix_ai_signal_performance_user_id'), table_name='ai_signal_performance')
    op.drop_index(op.f('ix_ai_signal_history_ticker'), table_name='ai_signal_history')
    op.drop_index(op.f('ix_ai_signal_history_user_id'), table_name='ai_signal_history')

    # 删除表
    op.drop_table('ai_signal_performance')
    op.drop_table('ai_signal_history')
