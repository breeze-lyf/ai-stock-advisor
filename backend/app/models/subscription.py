"""
会员体系和订阅模型
"""
from typing import Optional, Dict, Any
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Text, Numeric, JSON, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime, date
from app.core.database import Base


class SubscriptionPlan(Base):
    """
    订阅计划定义
    """
    __tablename__ = "subscription_plans"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # FREE/PRO/ENTERPRISE
    name_zh: Mapped[str] = mapped_column(String(100), nullable=False)  # 免费/专业/企业

    # 价格
    price_monthly: Mapped[float] = mapped_column(Numeric(10, 2), default=0)  # 月付价格
    price_yearly: Mapped[float] = mapped_column(Numeric(10, 2), default=0)  # 年付价格
    currency: Mapped[str] = mapped_column(String(10), default="CNY")

    # 功能限制
    daily_ai_analysis_limit: Mapped[int] = mapped_column(Integer, default=3)  # 每日 AI 分析次数
    notification_channels: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 可用的通知渠道
    screener_conditions_limit: Mapped[int] = mapped_column(Integer, default=3)  # 选股器条件数
    backtest_history_months: Mapped[int] = mapped_column(Integer, default=12)  # 回测历史长度（月）
    portfolio_stocks_limit: Mapped[int] = mapped_column(Integer, default=10)  # 持仓股票数上限
    data_refresh_delay_minutes: Mapped[int] = mapped_column(Integer, default=15)  # 数据刷新延迟

    # 教育课程
    course_access: Mapped[str] = mapped_column(String(20), default="BASIC")  # BASIC/ALL

    # 描述
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    features: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # 功能列表

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)


class UserSubscription(Base):
    """
    用户订阅记录
    """
    __tablename__ = "user_subscriptions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    plan_id: Mapped[str] = mapped_column(
        ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        index=True,
        nullable=False
    )

    # 订阅状态
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE/CANCELLED/EXPIRED/TRIAL

    # 订阅周期
    billing_cycle: Mapped[str] = mapped_column(String(20), default="MONTHLY")  # MONTHLY/YEARLY
    current_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    current_period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # 试用信息
    trial_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    trial_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    trial_used: Mapped[bool] = mapped_column(Boolean, default=False)

    # 支付信息
    payment_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # stripe/alipay/wechat
    payment_customer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payment_subscription_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 取消信息
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancel_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)

    # 关系
    plan = relationship("SubscriptionPlan")


class UsageRecord(Base):
    """
    用户使用量记录（用于限制）
    """
    __tablename__ = "usage_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    # 使用类型
    usage_type: Mapped[str] = mapped_column(String(50), nullable=False)  # AI_ANALYSIS/SCREENING/BACKTEST/etc.
    usage_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # 使用次数
    count: Mapped[int] = mapped_column(Integer, default=0)
    limit: Mapped[int] = mapped_column(Integer, default=0)  # 限制次数

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)


class PaymentTransaction(Base):
    """
    支付交易记录
    """
    __tablename__ = "payment_transactions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    subscription_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("user_subscriptions.id", ondelete="SET NULL"),
        index=True,
        nullable=True
    )

    # 交易信息
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)  # SUBSCRIPTION/REFUND/UPGRADE
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="CNY")

    # 支付状态
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING/COMPLETED/FAILED/REFUNDED
    payment_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # credit_card/alipay/wechat

    # 交易 ID
    provider_transaction_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    invoice_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 发票 URL

    # 错误信息
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # 元数据
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
