from pydantic import BaseModel

class AnalysisResponse(BaseModel):
    ticker: str
    analysis: str
    sentiment: str = "NEUTRAL"
