"""
监控和日志模型
用于 API 性能监控和错误追踪
"""
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Date, Text, Numeric, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
import uuid
from datetime import datetime, date
from app.core.database import Base


class APIMetric(Base):
    """
    API 性能指标
    记录每个 API 请求的响应时间和状态
    """
    __tablename__ = "api_metrics"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    endpoint: Mapped[str] = mapped_column(String(200), nullable=False, index=True)  # API 端点
    method: Mapped[str] = mapped_column(String(10), nullable=False)  # HTTP 方法
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)  # HTTP 状态码

    # 响应时间（毫秒）
    response_time_ms: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # 日期（用于按天聚合）
    request_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    request_hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 小时 (0-23)

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ErrorLog(Base):
    """
    错误日志
    记录所有未处理的异常
    """
    __tablename__ = "error_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    endpoint: Mapped[str] = mapped_column(String(200), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)

    # 错误信息
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)  # 异常类型
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # HTTP 信息
    status_code: Mapped[int] = mapped_column(Integer, default=500)
    request_body: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    client_ip: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 用户信息
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class SystemHealthCheck(Base):
    """
    系统健康检查记录
    定期检查各组件状态
    """
    __tablename__ = "system_health_checks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 组件状态
    database_status: Mapped[str] = mapped_column(String(20), default="UNKNOWN")  # OK/WARNING/ERROR/UNKNOWN
    redis_status: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    ai_provider_status: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    notification_status: Mapped[str] = mapped_column(String(20), default="UNKNOWN")

    # 性能指标
    active_connections: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_response_time_ms: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    error_rate_percent: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

    # 整体状态
    overall_status: Mapped[str] = mapped_column(String(20), default="UNKNOWN")  # OK/WARNING/ERROR

    # 详细信息
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 元数据
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class AlertRule(Base):
    """
    告警规则
    定义触发告警的条件
    """
    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # 告警类型
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ERROR_RATE/RESPONSE_TIME/SYSTEM_HEALTH
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)  # 监控指标名

    # 触发条件
    operator: Mapped[str] = mapped_column(String(10), nullable=False)  # >/</>=/<=/==/!=
    threshold: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=60)  # 持续多少秒触发

    # 通知配置
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_channels: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 逗号分隔

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AlertHistory(Base):
    """
    告警历史
    记录所有触发的告警
    """
    __tablename__ = "alert_history"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id: Mapped[Optional[str]] = mapped_column(String, index=True)

    # 告警信息
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    threshold: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="TRIGGERED")  # TRIGGERED/ACKNOWLEDGED/RESOLVED
    severity: Mapped[str] = mapped_column(String(20), default="WARNING")  # INFO/WARNING/ERROR/CRITICAL

    # 通知
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_channels: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # 处理
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 元数据
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
