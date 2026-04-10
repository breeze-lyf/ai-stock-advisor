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

from app.schemas.analysis import AnalysisResponse, PortfolioAnalysisResponse, StockCapsulesResponse

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


@router.get("/{ticker}/status")
async def get_analysis_status(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """轻量轮询端点：返回最新分析时间戳和陈旧状态，供前端 banner 判断是否有新版"""
    from datetime import datetime
    from app.infrastructure.db.repositories.scheduler_repository import SchedulerRepository
    from app.services.scheduler_jobs import should_auto_analyze

    repo = SchedulerRepository(db)
    report = await repo.get_latest_shared_analysis_report(ticker.upper())

    last_analyzed_at = None
    age_minutes: int | None = None
    is_stale = True

    if report:
        last_analyzed_at = report.created_at
        age_minutes = int((datetime.utcnow() - report.created_at).total_seconds() / 60)
        is_stale = should_auto_analyze(ticker, report)

    return {
        "ticker": ticker.upper(),
        "last_analyzed_at": last_analyzed_at,
        "age_minutes": age_minutes,
        "is_stale": is_stale,
    }


@router.get("/{ticker}", response_model=AnalysisResponse)
async def get_latest_analysis(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await GetLatestAnalysisUseCase(db, current_user).execute(ticker=ticker)


@router.get("/{ticker}/capsule", response_model=StockCapsulesResponse)
async def get_stock_capsules(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return pre-computed news + fundamental capsules for a ticker."""
    from app.application.analysis.generate_stock_capsule import GenerateStockCapsuleUseCase
    use_case = GenerateStockCapsuleUseCase(db)
    capsules = await use_case.get_capsules(ticker)

    def _to_resp(cap):
        if cap is None:
            return None
        return {
            "ticker": cap.ticker,
            "capsule_type": cap.capsule_type,
            "content": cap.content,
            "source_count": cap.source_count,
            "model_used": cap.model_used,
            "updated_at": cap.updated_at,
        }

    return {
        "ticker": ticker.upper(),
        "news": _to_resp(capsules.get("news")),
        "fundamental": _to_resp(capsules.get("fundamental")),
        "technical": _to_resp(capsules.get("technical")),
    }


@router.post("/{ticker}/capsule/refresh", response_model=StockCapsulesResponse)
async def refresh_stock_capsules(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger on-demand regeneration of both capsules for a ticker."""
    from app.application.analysis.generate_stock_capsule import GenerateStockCapsuleUseCase
    use_case = GenerateStockCapsuleUseCase(db)
    capsules = await use_case.generate_all(
        ticker,
        model=current_user.preferred_ai_model or None,
    )

    def _to_resp(cap):
        if cap is None:
            return None
        return {
            "ticker": cap.ticker,
            "capsule_type": cap.capsule_type,
            "content": cap.content,
            "source_count": cap.source_count,
            "model_used": cap.model_used,
            "updated_at": cap.updated_at,
        }

    return {
        "ticker": ticker.upper(),
        "news": _to_resp(capsules.get("news")),
        "fundamental": _to_resp(capsules.get("fundamental")),
        "technical": _to_resp(capsules.get("technical")),
    }
