from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text, JSON
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
    sentiment_score = Column(Enum(SentimentScore), nullable=True)
    model_used = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
