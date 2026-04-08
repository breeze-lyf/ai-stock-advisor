"""add_notification_settings_tables

Revision ID: 3c4d5e6f7a8b
Revises: 2b3c4d5e6f7a
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c4d5e6f7a8b'
down_revision: Union[str, None] = '2b3c4d5e6f7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建用户通知设置表
    op.create_table(
        'user_notification_settings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('email_enabled', sa.Boolean(), nullable=False, default=False),
        sa.Column('feishu_enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('browser_push_enabled', sa.Boolean(), nullable=False, default=False),
        sa.Column('sms_enabled', sa.Boolean(), nullable=False, default=False),
        sa.Column('quiet_mode_enabled', sa.Boolean(), nullable=False, default=False),
        sa.Column('quiet_mode_start', sa.String(length=5), nullable=True),
        sa.Column('quiet_mode_end', sa.String(length=5), nullable=True),
        sa.Column('p0_daily_limit', sa.Integer(), nullable=False, default=999),
        sa.Column('p1_daily_limit', sa.Integer(), nullable=False, default=20),
        sa.Column('p2_daily_limit', sa.Integer(), nullable=False, default=5),
        sa.Column('p3_daily_limit', sa.Integer(), nullable=False, default=10),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_user_notification_settings_user_id'),
        'user_notification_settings',
        ['user_id'],
        unique=True
    )

    # 创建用户通知订阅表
    op.create_table(
        'user_notification_subscriptions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('subscription_type', sa.String(length=50), nullable=False),
        sa.Column('target_id', sa.String(length=100), nullable=False),
        sa.Column('enable_price_alert', sa.Boolean(), nullable=False, default=True),
        sa.Column('enable_analysis_complete', sa.Boolean(), nullable=False, default=True),
        sa.Column('enable_news', sa.Boolean(), nullable=False, default=False),
        sa.Column('price_alert_above', sa.String(length=20), nullable=True),
        sa.Column('price_alert_below', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_user_notification_subscriptions_user_id'),
        'user_notification_subscriptions',
        ['user_id'],
        unique=False
    )

    # 创建浏览器推送订阅表
    op.create_table(
        'browser_push_subscriptions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('endpoint', sa.Text(), nullable=False),
        sa.Column('p256dh', sa.Text(), nullable=False),
        sa.Column('auth', sa.Text(), nullable=False),
        sa.Column('device_name', sa.String(length=100), nullable=True),
        sa.Column('browser', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_browser_push_subscriptions_user_id'),
        'browser_push_subscriptions',
        ['user_id'],
        unique=False
    )

    # 添加外键约束
    op.create_foreign_key(
        'fk_user_notification_settings_user',
        'user_notification_settings',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_user_notification_subscriptions_user',
        'user_notification_subscriptions',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_browser_push_subscriptions_user',
        'browser_push_subscriptions',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # 删除外键约束
    op.drop_constraint('fk_browser_push_subscriptions_user', 'browser_push_subscriptions', type_='foreignkey')
    op.drop_constraint('fk_user_notification_subscriptions_user', 'user_notification_subscriptions', type_='foreignkey')
    op.drop_constraint('fk_user_notification_settings_user', 'user_notification_settings', type_='foreignkey')

    # 删除索引
    op.drop_index(op.f('ix_browser_push_subscriptions_user_id'), table_name='browser_push_subscriptions')
    op.drop_index(op.f('ix_user_notification_subscriptions_user_id'), table_name='user_notification_subscriptions')
    op.drop_index(op.f('ix_user_notification_settings_user_id'), table_name='user_notification_settings')

    # 删除表
    op.drop_table('browser_push_subscriptions')
    op.drop_table('user_notification_subscriptions')
    op.drop_table('user_notification_settings')
