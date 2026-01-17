from sqlalchemy import Column, String, Float, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum

class MarketStatus(str, enum.Enum):
    PRE_MARKET = "PRE_MARKET"
    OPEN = "OPEN"
    AFTER_HOURS = "AFTER_HOURS"
    CLOSED = "CLOSED"

class Stock(Base):
    __tablename__ = "stocks"

    ticker = Column(String, primary_key=True, index=True)
    name = Column(String)
    sector = Column(String, nullable=True)
    exchange = Column(String, nullable=True)
    currency = Column(String, default="USD")

    # One-to-One relationship with MarketDataCache
    market_data = relationship("MarketDataCache", back_populates="stock", uselist=False)

class MarketDataCache(Base):
    __tablename__ = "market_data_cache"

    ticker = Column(String, ForeignKey("stocks.ticker"), primary_key=True)
    current_price = Column(Float)
    change_percent = Column(Float)
    rsi_14 = Column(Float, nullable=True)
    ma_20 = Column(Float, nullable=True)
    volume_ratio = Column(Float, nullable=True)
    market_status = Column(Enum(MarketStatus), default=MarketStatus.CLOSED)
    last_updated = Column(DateTime, default=datetime.utcnow, index=True)

    stock = relationship("Stock", back_populates="market_data")
