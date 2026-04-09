import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Integer, DateTime, UniqueConstraint

from app.core.database import Base


class StockCapsule(Base):
    """
    Pre-computed AI digest for a single ticker.

    capsule_type: "news" | "fundamental"
    - "news"        : Summarizes recent StockNews (25) + GlobalNews (10) headlines.
    - "fundamental" : Summarizes fundamental/valuation data from the Stock & MarketDataCache rows.

    One row per (ticker, capsule_type). Upsert on conflict.
    Refreshed every 24 h by the scheduler, or on-demand via the API.
    """

    __tablename__ = "stock_capsules"
    __table_args__ = (
        UniqueConstraint("ticker", "capsule_type", name="uq_stock_capsules_ticker_type"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ticker = Column(String, nullable=False, index=True)
    capsule_type = Column(String, nullable=False)  # "news" | "fundamental"
    content = Column(Text, nullable=True)           # AI Markdown output
    source_count = Column(Integer, default=0)       # how many items were fed in
    model_used = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
