"""add_subscription_tables

Revision ID: 7a8b9c0d1e2f
Revises: 6f7a8b9c0d1e
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a8b9c0d1e2f'
down_revision: Union[str, None] = '6f7a8b9c0d1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建订阅计划表
    op.create_table(
        'subscription_plans',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('name_zh', sa.String(length=100), nullable=False),
        sa.Column('price_monthly', sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column('price_yearly', sa.Numeric(10, 2), nullable=False, default=0),
        sa.Column('currency', sa.String(length=10), nullable=False, default='CNY'),
        sa.Column('daily_ai_analysis_limit', sa.Integer(), nullable=False, default=3),
        sa.Column('notification_channels', sa.String(length=100), nullable=True),
        sa.Column('screener_conditions_limit', sa.Integer(), nullable=False, default=3),
        sa.Column('backtest_history_months', sa.Integer(), nullable=False, default=12),
        sa.Column('portfolio_stocks_limit', sa.Integer(), nullable=False, default=10),
        sa.Column('data_refresh_delay_minutes', sa.Integer(), nullable=False, default=15),
        sa.Column('course_access', sa.String(length=20), nullable=False, default='BASIC'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建用户订阅表
    op.create_table(
        'user_subscriptions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('plan_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, default='ACTIVE'),
        sa.Column('billing_cycle', sa.String(length=20), nullable=False, default='MONTHLY'),
        sa.Column('current_period_start', sa.Date(), nullable=False),
        sa.Column('current_period_end', sa.Date(), nullable=False),
        sa.Column('trial_start', sa.Date(), nullable=True),
        sa.Column('trial_end', sa.Date(), nullable=True),
        sa.Column('trial_used', sa.Boolean(), nullable=False, default=False),
        sa.Column('payment_provider', sa.String(length=50), nullable=True),
        sa.Column('payment_customer_id', sa.String(length=100), nullable=True),
        sa.Column('payment_subscription_id', sa.String(length=100), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('cancel_reason', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_subscriptions_user_id'), 'user_subscriptions', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_subscriptions_plan_id'), 'user_subscriptions', ['plan_id'], unique=False)

    # 创建使用量记录表
    op.create_table(
        'usage_records',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('usage_type', sa.String(length=50), nullable=False),
        sa.Column('usage_date', sa.Date(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False, default=0),
        sa.Column('limit', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_usage_records_user_id'), 'usage_records', ['user_id'], unique=False)
    op.create_index(op.f('ix_usage_records_usage_date'), 'usage_records', ['usage_date'], unique=False)

    # 创建支付交易记录表
    op.create_table(
        'payment_transactions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('subscription_id', sa.String(), nullable=True),
        sa.Column('transaction_type', sa.String(length=20), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, default='CNY'),
        sa.Column('status', sa.String(length=20), nullable=False, default='PENDING'),
        sa.Column('payment_provider', sa.String(length=50), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('provider_transaction_id', sa.String(length=100), nullable=True),
        sa.Column('invoice_url', sa.String(length=500), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.String(length=500), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_transactions_user_id'), 'payment_transactions', ['user_id'], unique=False)
    op.create_index(op.f('ix_payment_transactions_subscription_id'), 'payment_transactions', ['subscription_id'], unique=False)

    # 添加外键约束
    op.create_foreign_key(
        'fk_user_subscriptions_user',
        'user_subscriptions',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_user_subscriptions_plan',
        'user_subscriptions',
        'subscription_plans',
        ['plan_id'],
        ['id'],
        ondelete='RESTRICT'
    )
    op.create_foreign_key(
        'fk_usage_records_user',
        'usage_records',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_payment_transactions_user',
        'payment_transactions',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_payment_transactions_subscription',
        'payment_transactions',
        'user_subscriptions',
        ['subscription_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # 插入默认订阅计划
    from datetime import datetime
    now = datetime.utcnow()
    op.bulk_insert(
        sa.table('subscription_plans',
            sa.column('id', sa.String()),
            sa.column('name', sa.String()),
            sa.column('name_zh', sa.String()),
            sa.column('price_monthly', sa.Numeric()),
            sa.column('price_yearly', sa.Numeric()),
            sa.column('currency', sa.String()),
            sa.column('daily_ai_analysis_limit', sa.Integer()),
            sa.column('screener_conditions_limit', sa.Integer()),
            sa.column('backtest_history_months', sa.Integer()),
            sa.column('portfolio_stocks_limit', sa.Integer()),
            sa.column('data_refresh_delay_minutes', sa.Integer()),
            sa.column('course_access', sa.String()),
            sa.column('is_active', sa.Boolean()),
            sa.column('sort_order', sa.Integer()),
            sa.column('created_at', sa.DateTime()),
        ),
        [
            {
                'id': 'free_plan_001',
                'name': 'FREE',
                'name_zh': '免费版',
                'price_monthly': 0,
                'price_yearly': 0,
                'currency': 'CNY',
                'daily_ai_analysis_limit': 3,
                'screener_conditions_limit': 3,
                'backtest_history_months': 6,
                'portfolio_stocks_limit': 10,
                'data_refresh_delay_minutes': 15,
                'course_access': 'BASIC',
                'is_active': True,
                'sort_order': 1,
                'created_at': now,
            },
            {
                'id': 'pro_plan_001',
                'name': 'PRO',
                'name_zh': '专业版',
                'price_monthly': 99,
                'price_yearly': 990,
                'currency': 'CNY',
                'daily_ai_analysis_limit': 999,
                'screener_conditions_limit': 999,
                'backtest_history_months': 60,
                'portfolio_stocks_limit': 50,
                'data_refresh_delay_minutes': 0,
                'course_access': 'ALL',
                'is_active': True,
                'sort_order': 2,
                'created_at': now,
            },
        ]
    )


def downgrade() -> None:
    # 删除外键约束
    op.drop_constraint('fk_payment_transactions_subscription', 'payment_transactions', type_='foreignkey')
    op.drop_constraint('fk_payment_transactions_user', 'payment_transactions', type_='foreignkey')
    op.drop_constraint('fk_usage_records_user', 'usage_records', type_='foreignkey')
    op.drop_constraint('fk_user_subscriptions_plan', 'user_subscriptions', type_='foreignkey')
    op.drop_constraint('fk_user_subscriptions_user', 'user_subscriptions', type_='foreignkey')

    # 删除索引
    op.drop_index(op.f('ix_payment_transactions_subscription_id'), table_name='payment_transactions')
    op.drop_index(op.f('ix_payment_transactions_user_id'), table_name='payment_transactions')
    op.drop_index(op.f('ix_usage_records_usage_date'), table_name='usage_records')
    op.drop_index(op.f('ix_usage_records_user_id'), table_name='usage_records')
    op.drop_index(op.f('ix_user_subscriptions_plan_id'), table_name='user_subscriptions')
    op.drop_index(op.f('ix_user_subscriptions_user_id'), table_name='user_subscriptions')

    # 删除表
    op.drop_table('payment_transactions')
    op.drop_table('usage_records')
    op.drop_table('user_subscriptions')
    op.drop_table('subscription_plans')
