import logging
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.application.analysis.analyze_stock import (
    AnalyzeStockUseCase,
)
from app.application.analysis.helpers import (
    extract_entry_prices_fallback,
    extract_entry_zone_fallback,
)
from app.application.analysis.analyze_portfolio import (
    AnalyzePortfolioUseCase,
    GetLatestPortfolioAnalysisUseCase,
)
from app.application.analysis.query_analysis import (
    GetAnalysisHistoryUseCase,
    GetLatestAnalysisUseCase,
)
from app.models.user import User
from app.api.deps import get_current_user

from app.schemas.analysis import AnalysisResponse, PortfolioAnalysisResponse

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/portfolio", response_model=PortfolioAnalysisResponse)
async def analyze_portfolio(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await AnalyzePortfolioUseCase(db, current_user).execute()

@router.get("/portfolio", response_model=PortfolioAnalysisResponse)
async def get_portfolio_analysis(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await GetLatestPortfolioAnalysisUseCase(db, current_user).execute()

@router.post("/{ticker}", response_model=AnalysisResponse)
async def analyze_stock(
    ticker: str, 
    force: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await AnalyzeStockUseCase(db, current_user).execute(ticker=ticker, force=force)


@router.get("/{ticker}/history", response_model=List[AnalysisResponse])
async def get_analysis_history(
    ticker: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await GetAnalysisHistoryUseCase(db, current_user).execute(ticker=ticker, limit=limit)

@router.get("/{ticker}", response_model=AnalysisResponse)
async def get_latest_analysis(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await GetLatestAnalysisUseCase(db, current_user).execute(ticker=ticker)
