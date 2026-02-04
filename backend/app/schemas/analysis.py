from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AnalysisResponse(BaseModel):
    ticker: str
    analysis: str
    sentiment: str = "NEUTRAL"
    is_cached: bool = False
    model_used: Optional[str] = None
    created_at: Optional[datetime] = None
