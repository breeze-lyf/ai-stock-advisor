"""
通知分级和静默时段模型
"""
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime
from app.core.database import Base
import enum


class NotificationPriority(str, enum.Enum):
    """通知优先级"""
    P0 = "P0"  # 紧急：止损触发、重大利空
    P1 = "P1"  # 高：目标价接近、加仓信号
    P2 = "P2"  # 中：常规复盘、周报
    P3 = "P3"  # 低：市场资讯、快讯


class UserNotificationSetting(Base):
    """
    用户通知设置
    """
    __tablename__ = "user_notification_settings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False
    )

    # 通知渠道启用状态
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    feishu_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    browser_push_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # 静默时段设置
    quiet_mode_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    quiet_mode_start: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM 格式
    quiet_mode_end: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM 格式

    # 各优先级通知的频率限制（条/日）
    p0_daily_limit: Mapped[int] = mapped_column(Integer, default=999)  # P0 无限制
    p1_daily_limit: Mapped[int] = mapped_column(Integer, default=20)
    p2_daily_limit: Mapped[int] = mapped_column(Integer, default=5)
    p3_daily_limit: Mapped[int] = mapped_column(Integer, default=10)

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)


class UserNotificationSubscription(Base):
    """
    用户通知订阅（按标的/主题）
    """
    __tablename__ = "user_notification_subscriptions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    # 订阅类型
    subscription_type: Mapped[str] = mapped_column(String(50), nullable=False)  # ticker, sector, topic

    # 订阅目标
    target_id: Mapped[str] = mapped_column(String(100), nullable=False)  # 股票代码/行业/主题

    # 通知类型
    enable_price_alert: Mapped[bool] = mapped_column(Boolean, default=True)  # 价格预警
    enable_analysis_complete: Mapped[bool] = mapped_column(Boolean, default=True)  # AI 分析完成
    enable_news: Mapped[bool] = mapped_column(Boolean, default=False)  # 相关新闻

    # 价格预警配置
    price_alert_above: Mapped[Optional[float]] = mapped_column(String(20), nullable=True)  # 突破某价格
    price_alert_below: Mapped[Optional[float]] = mapped_column(String(20), nullable=True)  # 跌破某价格

    # 元数据
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BrowserPushSubscription(Base):
    """
    浏览器推送订阅
    """
    __tablename__ = "browser_push_subscriptions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    # 推送端点信息
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)  # 用户公钥
    auth: Mapped[str] = mapped_column(Text, nullable=False)  # 认证密钥

    # 设备信息
    device_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    browser: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
