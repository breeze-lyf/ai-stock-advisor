"""
AI 信号历史记录模型
用于追踪 AI 分析建议的发布价格和后续表现
"""
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Text, Numeric, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime
from app.core.database import Base
import enum


class SignalType(str, enum.Enum):
    """AI 信号类型"""
    BUY = "BUY"  # 买入
    SELL = "SELL"  # 卖出
    HOLD = "HOLD"  # 持有
    STRONG_BUY = "STRONG_BUY"  # 强烈买入
    STRONG_SELL = "STRONG_SELL"  # 强烈卖出


class SignalStatus(str, enum.Enum):
    """信号状态"""
    ACTIVE = "ACTIVE"  # 有效中
    CLOSED = "CLOSED"  # 已关闭（已止盈/止损）
    EXPIRED = "EXPIRED"  # 已过期
    CANCELLED = "CANCELLED"  # 已取消


class AISignalHistory(Base):
    """
    AI 信号历史记录
    记录每次 AI 分析生成的投资建议及其后续表现
    """
    __tablename__ = "ai_signal_history"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    ticker: Mapped[str] = mapped_column(String(20), index=True, nullable=False)

    # 信号信息
    signal_type: Mapped[SignalType] = mapped_column(SQLEnum(SignalType), nullable=False)
    signal_status: Mapped[SignalStatus] = mapped_column(SQLEnum(SignalStatus), default=SignalStatus.ACTIVE)

    # 发布时的价格信息
    entry_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)  # 发布时的价格
    target_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)  # 目标价
    stop_loss_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)  # 止损价

    # AI 分析置信度
    confidence_score: Mapped[int] = mapped_column(Integer, default=50)  # 0-100
    time_horizon: Mapped[str] = mapped_column(String(20), default="SHORT")  # SHORT/MEDIUM/LONG

    # 信号逻辑
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # AI 分析逻辑
    key_factors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 关键因素（JSON 数组）

    # 结果追踪
    exit_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)  # 退出价格
    exit_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 退出原因 (TARGET_HIT/STOP_LOSS/TIME_EXPIRED/MANUAL)

    # 表现指标
    pnl_percent: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)  # 盈亏百分比
    pnl_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)  # 盈亏金额（假设 1 手）
    max_drawdown: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)  # 最大回撤
    max_gain: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)  # 最大浮盈

    # 元数据
    analysis_report_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("analysis_reports.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关系
    analysis_report = relationship("AnalysisReport", back_populates="ai_signals")


class AISignalPerformance(Base):
    """
    AI 信号表现统计（按用户/股票/时间段聚合）
    """
    __tablename__ = "ai_signal_performance"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    # 统计周期
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # DAILY/WEEKLY/MONTHLY/YEARLY
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # 信号统计
    total_signals: Mapped[int] = mapped_column(Integer, default=0)
    closed_signals: Mapped[int] = mapped_column(Integer, default=0)
    winning_signals: Mapped[int] = mapped_column(Integer, default=0)
    losing_signals: Mapped[int] = mapped_column(Integer, default=0)

    # 表现指标
    win_rate: Mapped[float] = mapped_column(Numeric(6, 4), default=0)  # 胜率
    avg_pnl_percent: Mapped[float] = mapped_column(Numeric(10, 4), default=0)  # 平均盈亏
    avg_gain_percent: Mapped[float] = mapped_column(Numeric(10, 4), default=0)  # 平均盈利
    avg_loss_percent: Mapped[float] = mapped_column(Numeric(10, 4), default=0)  # 平均亏损
    profit_factor: Mapped[float] = mapped_column(Numeric(6, 4), default=0)  # 盈利因子

    # 最佳/最差表现
    best_signal_ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    best_signal_pnl: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    worst_signal_ticker: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    worst_signal_pnl: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)
