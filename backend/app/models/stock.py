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
    industry = Column(String, nullable=True)
    market_cap = Column(Float, nullable=True)
    pe_ratio = Column(Float, nullable=True)
    forward_pe = Column(Float, nullable=True)
    eps = Column(Float, nullable=True)
    dividend_yield = Column(Float, nullable=True)
    beta = Column(Float, nullable=True)
    fifty_two_week_high = Column(Float, nullable=True)
    fifty_two_week_low = Column(Float, nullable=True)
    exchange = Column(String, nullable=True)
    currency = Column(String, default="USD")

    # One-to-One relationship with MarketDataCache
    market_data = relationship("MarketDataCache", back_populates="stock", uselist=False)

class MarketDataCache(Base):
    __tablename__ = "market_data_cache"

    ticker = Column(String, ForeignKey("stocks.ticker"), primary_key=True)
    current_price = Column(Float)
    change_percent = Column(Float)
    
    # Technical Indicators for LLM
    rsi_14 = Column(Float, nullable=True)
    ma_20 = Column(Float, nullable=True)
    ma_50 = Column(Float, nullable=True)
    ma_200 = Column(Float, nullable=True)
    macd_val = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_hist = Column(Float, nullable=True)
    
    # Bollinger Bands
    bb_upper = Column(Float, nullable=True)
    bb_middle = Column(Float, nullable=True)
    bb_lower = Column(Float, nullable=True)
    
    # ATR & KDJ
    atr_14 = Column(Float, nullable=True)
    k_line = Column(Float, nullable=True)
    d_line = Column(Float, nullable=True)
    j_line = Column(Float, nullable=True)
    
    # Volume
    volume_ma_20 = Column(Float, nullable=True)
    volume_ratio = Column(Float, nullable=True)
    
    market_status = Column(String, default=MarketStatus.CLOSED.value)
    last_updated = Column(DateTime, default=datetime.utcnow, index=True)

    stock = relationship("Stock", back_populates="market_data")

class StockNews(Base):
    __tablename__ = "stock_news"

    id = Column(String, primary_key=True) # Usually Yahoo provides a UUID or ID
    ticker = Column(String, ForeignKey("stocks.ticker"), index=True)
    title = Column(String, nullable=False)
    publisher = Column(String, nullable=True)
    link = Column(String, nullable=False)
    publish_time = Column(DateTime, nullable=False)
    summary = Column(String, nullable=True)
    sentiment = Column(String, nullable=True) # Prepared for future AI sentiment tagging
    
    stock = relationship("Stock", back_populates="news")

Stock.news = relationship("StockNews", back_populates="stock", cascade="all, delete-orphan")
Stock.market_data = relationship("MarketDataCache", back_populates="stock", uselist=False)
