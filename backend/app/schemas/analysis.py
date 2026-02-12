from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class AnalysisResponse(BaseModel):
    ticker: str
    analysis: Optional[str] = None
    sentiment_score: Optional[float] = None
    summary_status: Optional[str] = None
    risk_level: Optional[str] = None
    technical_analysis: Optional[str] = None
    fundamental_news: Optional[str] = None
    action_advice: Optional[str] = None
    investment_horizon: Optional[str] = None
    confidence_level: Optional[float] = None
    immediate_action: Optional[str] = None
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    entry_zone: Optional[str] = None
    entry_price_low: Optional[float] = None
    entry_price_high: Optional[float] = None
    rr_ratio: Optional[str] = None
    is_cached: bool = False
    model_used: Optional[str] = None
    created_at: Optional[datetime] = None

class PortfolioAnalysisResponse(BaseModel):
    health_score: int
    risk_level: str
    summary: str
    diversification_analysis: str
    strategic_advice: str
    top_risks: List[str]
    top_opportunities: List[str]
    detailed_report: str
    model_used: Optional[str] = None
    created_at: datetime
