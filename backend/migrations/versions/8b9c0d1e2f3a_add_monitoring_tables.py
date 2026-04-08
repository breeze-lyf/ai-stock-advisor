"""add_monitoring_tables

Revision ID: 8b9c0d1e2f3a
Revises: 7a8b9c0d1e2f
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b9c0d1e2f3a'
down_revision: Union[str, None] = '7a8b9c0d1e2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 API 性能指标表
    op.create_table(
        'api_metrics',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('endpoint', sa.String(length=200), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('response_time_ms', sa.Numeric(10, 2), nullable=False),
        sa.Column('request_date', sa.Date(), nullable=False),
        sa.Column('request_hour', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_api_metrics_endpoint'), 'api_metrics', ['endpoint'], unique=False)
    op.create_index(op.f('ix_api_metrics_request_date'), 'api_metrics', ['request_date'], unique=False)
    op.create_index(op.f('ix_api_metrics_created_at'), 'api_metrics', ['created_at'], unique=False)

    # 创建错误日志表
    op.create_table(
        'error_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('endpoint', sa.String(length=200), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=False),
        sa.Column('error_type', sa.String(length=100), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=False, default=500),
        sa.Column('request_body', sa.JSON(), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('client_ip', sa.String(length=50), nullable=True),
        sa.Column('user_id', sa.String(length=100), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False, default=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_error_logs_user_id'), 'error_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_error_logs_created_at'), 'error_logs', ['created_at'], unique=False)

    # 创建系统健康检查表
    op.create_table(
        'system_health_checks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('database_status', sa.String(length=20), nullable=False, default='UNKNOWN'),
        sa.Column('redis_status', sa.String(length=20), nullable=False, default='UNKNOWN'),
        sa.Column('ai_provider_status', sa.String(length=20), nullable=False, default='UNKNOWN'),
        sa.Column('notification_status', sa.String(length=20), nullable=False, default='UNKNOWN'),
        sa.Column('active_connections', sa.Integer(), nullable=True),
        sa.Column('avg_response_time_ms', sa.Numeric(10, 2), nullable=True),
        sa.Column('error_rate_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('overall_status', sa.String(length=20), nullable=False, default='UNKNOWN'),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('checked_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_health_checks_checked_at'), 'system_health_checks', ['checked_at'], unique=False)

    # 创建告警规则表
    op.create_table(
        'alert_rules',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('operator', sa.String(length=10), nullable=False),
        sa.Column('threshold', sa.Numeric(10, 4), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=False, default=60),
        sa.Column('enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('notification_channels', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_triggered_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建告警历史表
    op.create_table(
        'alert_history',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('rule_id', sa.String(), nullable=True),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.Numeric(10, 4), nullable=False),
        sa.Column('threshold', sa.Numeric(10, 4), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, default='TRIGGERED'),
        sa.Column('severity', sa.String(length=20), nullable=False, default='WARNING'),
        sa.Column('notification_sent', sa.Boolean(), nullable=False, default=False),
        sa.Column('notification_channels', sa.String(length=200), nullable=True),
        sa.Column('acknowledged_by', sa.String(length=100), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_by', sa.String(length=100), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('triggered_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_history_rule_id'), 'alert_history', ['rule_id'], unique=False)
    op.create_index(op.f('ix_alert_history_triggered_at'), 'alert_history', ['triggered_at'], unique=False)

    # 插入默认告警规则
    from datetime import datetime
    now = datetime.utcnow()
    op.bulk_insert(
        sa.table('alert_rules',
            sa.column('id', sa.String()),
            sa.column('name', sa.String()),
            sa.column('description', sa.String()),
            sa.column('alert_type', sa.String()),
            sa.column('metric_name', sa.String()),
            sa.column('operator', sa.String()),
            sa.column('threshold', sa.Numeric()),
            sa.column('duration_seconds', sa.Integer()),
            sa.column('enabled', sa.Boolean()),
            sa.column('created_at', sa.DateTime()),
        ),
        [
            {
                'id': 'alert_error_rate_001',
                'name': 'High Error Rate',
                'description': 'Error rate exceeds 5%',
                'alert_type': 'ERROR_RATE',
                'metric_name': 'error_rate_percent',
                'operator': '>',
                'threshold': 5.0,
                'duration_seconds': 300,
                'enabled': True,
                'created_at': now,
            },
            {
                'id': 'alert_response_time_001',
                'name': 'Slow Response Time',
                'description': 'Average response time exceeds 1000ms',
                'alert_type': 'RESPONSE_TIME',
                'metric_name': 'avg_response_time_ms',
                'operator': '>',
                'threshold': 1000.0,
                'duration_seconds': 300,
                'enabled': True,
                'created_at': now,
            },
        ]
    )


def downgrade() -> None:
    # 删除表
    op.drop_table('alert_history')
    op.drop_table('alert_rules')
    op.drop_table('system_health_checks')
    op.drop_table('error_logs')
    op.drop_table('api_metrics')
