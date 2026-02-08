from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text, JSON, Float
import uuid
from datetime import datetime
from app.core.database import Base
import enum

class SentimentScore(str, enum.Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    ticker = Column(String, ForeignKey("stocks.ticker"), nullable=False)
    
    input_context_snapshot = Column(JSON)
    ai_response_markdown = Column(Text)
    
    # Structured fields
    sentiment_score = Column(String, nullable=True) # Score 0-100
    summary_status = Column(String, nullable=True)  # Short status phrase
    risk_level = Column(String, nullable=True)      # LOW/MEDIUM/HIGH
    technical_analysis = Column(Text, nullable=True)
    fundamental_news = Column(Text, nullable=True)
    action_advice = Column(Text, nullable=True)
    investment_horizon = Column(String, nullable=True) # Short-term, Mid-term, Long-term
    confidence_level = Column(Float, nullable=True)    # 0-100
    immediate_action = Column(String, nullable=True)  # e.g., Buy, Hold, Sell
    target_price = Column(Float, nullable=True)
    stop_loss_price = Column(Float, nullable=True)
    entry_zone = Column(String, nullable=True)      # e.g., "$88.5 - $90.0" (Wait for full migration, keeping for compatibility)
    entry_price_low = Column(Float, nullable=True)
    entry_price_high = Column(Float, nullable=True)
    rr_ratio = Column(String, nullable=True)        # e.g., "1:3"
    
    model_used = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
