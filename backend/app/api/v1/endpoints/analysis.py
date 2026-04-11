import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, BackgroundTasks
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
    from app.application.analysis.query_analysis import GetLatestAnalysisUseCase

    last_analyzed_at = None
    age_minutes: int | None = None
    is_stale = True

    # 使用与主接口相同的逻辑获取最新有效报告（跳过 error 报告），
    # 避免 error 报告导致时间戳不匹配而误触发 banner
    report = await GetLatestAnalysisUseCase(db, current_user)._get_latest_shared_report(ticker.upper())

    if report:
        last_analyzed_at = report.created_at
        age_minutes = int((datetime.utcnow() - report.created_at).total_seconds() / 60)
        scheduler_repo = SchedulerRepository(db)
        latest_raw = await scheduler_repo.get_latest_shared_analysis_report(ticker.upper())
        is_stale = should_auto_analyze(ticker, latest_raw) if latest_raw else True

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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger on-demand regeneration of capsules for a ticker.

    Step 1: Force-refresh market data (price, fundamentals, technicals, news)
            so the capsules are built from the latest information.
    Step 2: Return existing capsules immediately (non-blocking).
    Step 3: Regenerate capsules in background via BackgroundTasks.

    This prevents request timeout during slow AI generation.
    """
    from app.application.analysis.generate_stock_capsule import GenerateStockCapsuleUseCase
    from app.services.market_data import MarketDataService

    ticker = ticker.upper().strip()

    # Step 1: Refresh market data (force=True fetches news, technicals, fundamentals fresh)
    # Cap at 60s so the AI capsule generation step still has time within the overall request budget.
    try:
        import asyncio
        await asyncio.wait_for(
            MarketDataService.get_real_time_data(
                ticker,
                db,
                preferred_source=current_user.preferred_data_source or "AUTO",
                force_refresh=True,
                price_only=False,
                skip_news=False,
                user_id=current_user.id,
            ),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        logger.warning(f"[CapsuleRefresh] Market data pre-refresh timed out for {ticker}, proceeding with cached data")
    except Exception as exc:
        logger.warning(f"[CapsuleRefresh] Market data pre-refresh failed for {ticker}, proceeding with cached data: {exc}")

    # Step 2: Return existing capsules immediately (don't wait for AI generation)
    use_case = GenerateStockCapsuleUseCase(db)
    existing_capsules = await use_case.get_capsules(ticker)

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

    # Step 3: Schedule background regeneration
    background_tasks.add_task(
        _background_capsule_generation,
        ticker,
        current_user.preferred_ai_model,
        current_user.id,
    )

    return {
        "ticker": ticker.upper(),
        "news": _to_resp(existing_capsules.get("news")),
        "fundamental": _to_resp(existing_capsules.get("fundamental")),
        "technical": _to_resp(existing_capsules.get("technical")),
    }


async def _background_capsule_generation(
    ticker: str,
    preferred_model: Optional[str],
    user_id: str,
):
    """Background task to regenerate capsules after market data refresh."""
    from app.core.database import SessionLocal
    from app.application.analysis.generate_stock_capsule import GenerateStockCapsuleUseCase

    async with SessionLocal() as db:
        try:
            use_case = GenerateStockCapsuleUseCase(db)
            await use_case.generate_all(
                ticker,
                model=preferred_model,
            )
            logger.info(f"[CapsuleRefresh] Background capsule generation completed for {ticker}")
        except Exception as exc:
            logger.error(f"[CapsuleRefresh] Background capsule generation failed for {ticker}: {exc}")
