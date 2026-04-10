from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class StockCapsuleResponse(BaseModel):
    ticker: str
    capsule_type: str
    content: Optional[str] = None
    source_count: Optional[int] = None
    model_used: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StockCapsulesResponse(BaseModel):
    ticker: str
    news: Optional[StockCapsuleResponse] = None
    fundamental: Optional[StockCapsuleResponse] = None
    technical: Optional[StockCapsuleResponse] = None


class AnalysisResponse(BaseModel):
    ticker: str
    analysis: Optional[str] = None
    decision_mode: Optional[str] = None
    dominant_driver: Optional[str] = None
    trade_setup_status: Optional[str] = None
    sentiment_score: Optional[float] = None
    summary_status: Optional[str] = None
    risk_level: Optional[str] = None
    trigger_condition: Optional[str] = None
    invalidation_condition: Optional[str] = None
    next_review_point: Optional[str] = None
    technical_analysis: Optional[str] = None
    fundamental_news: Optional[str] = None
    news_summary: Optional[str] = None
    fundamental_analysis: Optional[str] = None
    macro_risk_note: Optional[str] = None
    add_on_trigger: Optional[str] = None
    target_price_1: Optional[float] = None
    target_price_2: Optional[float] = None
    max_position_pct: Optional[float] = None
    bull_case: Optional[str] = None
    base_case: Optional[str] = None
    bear_case: Optional[str] = None
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
    report_scope: Optional[str] = None
    created_at: Optional[datetime] = None
    history_price: Optional[float] = None
    # Truth Tracker 2.0 & Phase 2
    max_drawdown: Optional[float] = None
    max_favorable_excursion: Optional[float] = None
    scenario_tags: Optional[List[dict]] = None
    audit_notes: Optional[str] = None
    thought_process: Optional[List[dict]] = None

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
