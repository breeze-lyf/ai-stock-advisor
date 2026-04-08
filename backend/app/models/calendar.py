"""
财经日历模型
存储宏观经济事件、财报发布等日历事件
"""
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Integer, Text, Date, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime, date
from app.core.database import Base


class EconomicEvent(Base):
    """
    宏观经济事件
    如：美联储议息会议、CPI 数据、非农就业等
    """
    __tablename__ = "economic_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 事件基本信息
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 事件类型

    # 事件时间
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    event_time: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 具体时间
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")

    # 事件来源国家/地区
    country: Mapped[str] = mapped_column(String(50), nullable=False)  # 如：US, CN, EU
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 重要性等级 (1-3 星)
    importance: Mapped[int] = mapped_column(Integer, default=2)  # 1=低，2=中，3=高

    # 预期值/前值/实际值
    forecast: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    previous: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 影响分析
    impact_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    affected_sectors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON 数组

    # 元数据
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)

    # 是否已推送
    is_pushed: Mapped[bool] = mapped_column(Boolean, default=False)


class EarningsEvent(Base):
    """
    财报发布事件
    """
    __tablename__ = "earnings_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 公司信息
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # 财报类型
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)  # Q1, Q2, Q3, Q4, Annual
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    fiscal_quarter: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 发布时间
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    report_time: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # Before/After Market
    timezone: Mapped[str] = mapped_column(String(50), default="America/New_York")

    # 预期数据
    eps_estimate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eps_actual: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    revenue_estimate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    revenue_actual: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 影响分析
    market_reaction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 市场反应
    analyst_commentary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 分析师评论

    # 元数据
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)

    # 是否已推送
    is_pushed: Mapped[bool] = mapped_column(Boolean, default=False)


class UserCalendarAlert(Base):
    """
    用户日历提醒设置
    """
    __tablename__ = "user_calendar_alerts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # 提醒类型
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # economic, earnings
    event_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # 关联的事件 ID

    # 提醒条件
    ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 特定股票
    country: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 特定国家
    importance_min: Mapped[int] = mapped_column(Integer, default=2)  # 最小重要性

    # 提醒时间
    remind_before_minutes: Mapped[int] = mapped_column(Integer, default=30)  # 提前多少分钟提醒

    # 元数据
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
