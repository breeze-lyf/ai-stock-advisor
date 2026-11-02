"""P2 agent tables: daily briefs, notifier channels, advice records (复盘)."""
from datetime import datetime
import uuid
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class AgentDailyBrief(Base):
    __tablename__ = "agent_daily_briefs"
    __table_args__ = (UniqueConstraint("user_id", "brief_date", name="uq_agent_brief_user_date"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    brief_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD (Asia/Shanghai)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="今日简报")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tickers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")  # ok | error
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pushed_channels: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentNotifierConfig(Base):
    """Per-user push channel for briefs. kind: dingtalk | webhook | telegram."""
    __tablename__ = "agent_notifier_configs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False, default="")  # webhook url / telegram chat_id
    secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # dingtalk sign secret / telegram bot token
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    brief_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_status: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentAdviceRecord(Base):
    """An actionable recommendation captured from diagnosis/agent, evaluated after its horizon."""
    __tablename__ = "agent_advice_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY | SELL | HOLD
    price_at: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    target_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="diagnosis")  # diagnosis | agent | brief
    conversation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)  # open | evaluated | error
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    eval_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    return_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hit: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
