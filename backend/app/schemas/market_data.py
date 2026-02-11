from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

class MarketStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PRE_MARKET = "PRE_MARKET"
    POST_MARKET = "POST_MARKET"

class ProviderQuote(BaseModel):
    ticker: str
    price: float
    change: float = 0.0
    change_percent: float = 0.0
    name: Optional[str] = None
    market_status: MarketStatus = MarketStatus.OPEN
    last_updated: Optional[datetime] = None

class ProviderFundamental(BaseModel):
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

class ProviderNews(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    publisher: Optional[str] = None
    link: Optional[str] = None
    summary: Optional[str] = None
    publish_time: datetime

class ProviderTechnical(BaseModel):
    indicators: Dict[str, Optional[float]] = Field(default_factory=dict)

class FullMarketData(BaseModel):
    quote: ProviderQuote
    fundamental: Optional[ProviderFundamental] = None
    technical: Optional[ProviderTechnical] = None
    news: List[ProviderNews] = Field(default_factory=list)

class OHLCVItem(BaseModel):
    time: str  # YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    # Technical Indicators for Charting
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
