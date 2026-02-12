from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class SectorExposure(BaseModel):
    sector: str
    weight: float
    value: float

class PortfolioSummary(BaseModel):
    total_market_value: float
    total_unrealized_pl: float
    total_pl_percent: float
    day_change: float
    holdings: List[PortfolioItem]
    sector_exposure: List[SectorExposure]

class PortfolioItem(BaseModel):
    ticker: str
    name: Optional[str] = None
    quantity: float
    avg_cost: float
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pl: float = 0.0
    pl_percent: float = 0.0
    last_updated: Optional[datetime] = None
    
    # Fundamental fields
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    eps: Optional[float] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    
    # Technical indicator fields
    rsi_14: Optional[float] = None
    ma_20: Optional[float] = None
    ma_50: Optional[float] = None
    ma_200: Optional[float] = None
    macd_val: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    macd_hist_slope: Optional[float] = None
    macd_cross: Optional[str] = None
    macd_is_new_cross: bool = False
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    atr_14: Optional[float] = None
    k_line: Optional[float] = None
    d_line: Optional[float] = None
    j_line: Optional[float] = None
    volume_ma_20: Optional[float] = None
    volume_ratio: Optional[float] = None
    # ADX & 支撑阻力位
    adx_14: Optional[float] = None
    pivot_point: Optional[float] = None
    resistance_1: Optional[float] = None
    resistance_2: Optional[float] = None
    support_1: Optional[float] = None
    support_2: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    
    change_percent: Optional[float] = 0.0

class PortfolioCreate(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float

class SearchResult(BaseModel):
    ticker: str
    name: str
