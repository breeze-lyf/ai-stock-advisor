from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum
from app.core.database import Base

class TradeStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED_PROFIT = "CLOSED_PROFIT"
    CLOSED_LOSS = "CLOSED_LOSS"
    CLOSED_MANUAL = "CLOSED_MANUAL"

class SimulatedTrade(Base):
    """
    模拟交易表 (Paper Trading)
    """
    __tablename__ = "simulated_trades"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    ticker = Column(String, ForeignKey("stocks.ticker"), nullable=False, index=True)
    
    # 状态
    status = Column(Enum(TradeStatus), default=TradeStatus.OPEN, nullable=False, index=True)
    
    # 入场信息
    entry_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    entry_price = Column(Float, nullable=False)
    # AI 当时开仓时的原因 (可以直接存诊断分析 ID，也可以直接文本)
    entry_reason = Column(Text, nullable=True)
    
    # 期望目标与底线
    target_price = Column(Float, nullable=True)
    stop_loss_price = Column(Float, nullable=True)
    
    # 当前追踪信息
    current_price = Column(Float, nullable=True) # 每日盘后更新
    unrealized_pnl_pct = Column(Float, nullable=True) # 账面浮亏浮盈比
    
    # 离场信息
    exit_date = Column(DateTime, nullable=True)
    exit_price = Column(Float, nullable=True)
    realized_pnl_pct = Column(Float, nullable=True) # 最终落袋盈亏
    exit_reason = Column(Text, nullable=True)
    
    # 关联
    user = relationship("User", back_populates="simulated_trades")
    stock = relationship("Stock", back_populates="simulated_trades")
    logs = relationship("TradeHistoryLog", back_populates="trade", cascade="all, delete-orphan")


class TradeHistoryLog(Base):
    """
    单笔交易每日的价格追踪记录
    用于绘制单笔订单的资金持股曲线
    """
    __tablename__ = "trade_history_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trade_id = Column(String, ForeignKey("simulated_trades.id"), nullable=False, index=True)
    
    log_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    price = Column(Float, nullable=False)
    pnl_pct = Column(Float, nullable=False) # 当日的账面盈亏
    
    trade = relationship("SimulatedTrade", back_populates="logs")
