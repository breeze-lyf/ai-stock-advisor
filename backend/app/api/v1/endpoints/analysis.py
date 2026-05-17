import asyncio
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db, SessionLocal
from app.core.rate_limiter import limiter
from app.application.analysis.analyze_stock import (
    AnalyzeStockUseCase,
)
from app.infrastructure.db.repositories.analysis_repository import AnalysisRepository
from app.services.ai_service import AIService
from app.application.analysis.analyze_portfolio import (
    AnalyzePortfolioUseCase,
    GetLatestPortfolioAnalysisUseCase,
)
from app.infrastructure.db.repositories.portfolio_repository import PortfolioRepository
from app.application.analysis.query_analysis import (
    GetAnalysisHistoryUseCase,
    GetLatestAnalysisUseCase,
)
from app.models.user import User
from app.api.deps import get_current_user
from app.services.domain.market.market_data import MarketDataService

from app.schemas.analysis import AnalysisResponse, PortfolioAnalysisResponse, StockCapsulesResponse
from app.application.analysis.generate_stock_capsule import GenerateStockCapsuleUseCase
from app.application.analysis.helpers import find_latest_shared_report
from app.utils.time import utc_now_naive
from app.infrastructure.db.repositories.scheduler_repository import SchedulerRepository
from app.services.scheduler.scheduler_jobs import should_auto_analyze

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/portfolio", response_model=PortfolioAnalysisResponse)
@limiter.limit("5/minute")
async def analyze_portfolio(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    一键分析全量持仓组合。

    【业务逻辑】
    - 获取当前用户所有的持仓标的。
    - 将资产组合数据喂给 AI 模型。
    - 生成宏观视角下的风险建议和调仓逻辑。
    """
    use_case = AnalyzePortfolioUseCase(
        portfolio_repo=PortfolioRepository(db),
        ai_service=AIService(db=db, user=current_user),
        current_user=current_user,
        db=db,
    )
    return await use_case.execute()

@router.get("/portfolio", response_model=PortfolioAnalysisResponse)
async def get_portfolio_analysis(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    use_case = GetLatestPortfolioAnalysisUseCase(
        db=db,
        current_user=current_user,
        portfolio_repo=PortfolioRepository(db),
    )
    return await use_case.execute()

@router.post("/{ticker}", response_model=AnalysisResponse)
@limiter.limit("10/minute")
async def analyze_stock(
    request: Request,
    ticker: str,
    force: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    针对单只股票发起全量 AI 研判。
    
    【核心逻辑】
    这是本系统最核心且最耗时的功能：
    - 启动并行数据抓取任务（报价/新闻/财务/宏观）。
    - 构造上下文并调用 AI 大模型（如 DeepSeek-R1）。
    - 解析并持久化一份具备买入/卖出倾向的分析报告。
    """
    use_case = AnalyzeStockUseCase(
        analysis_repo=AnalysisRepository(db),
        ai_service=AIService(db=db, user=current_user),
        current_user=current_user,
        db=db,
    )
    return await use_case.execute(ticker=ticker, force=force)


@router.get("/{ticker}/history", response_model=List[AnalysisResponse])
async def get_analysis_history(
    ticker: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    use_case = GetAnalysisHistoryUseCase(
        db=db,
        current_user=current_user,
        analysis_repo=AnalysisRepository(db),
    )
    return await use_case.execute(ticker=ticker, limit=limit)


@router.get("/{ticker}/status")
async def get_analysis_status(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """轻量轮询端点：返回最新分析时间戳和陈旧状态，供前端 banner 判断是否有新版"""
    last_analyzed_at = None
    age_minutes: int | None = None
    is_stale = True

    # 使用与主接口相同的逻辑获取最新有效报告（跳过 error 报告），
    # 避免 error 报告导致时间戳不匹配而误触发 banner
    repo = AnalysisRepository(db)
    report = await find_latest_shared_report(repo, ticker.upper(), current_user.preferred_ai_model)

    if report:
        last_analyzed_at = report.created_at
        age_minutes = int((utc_now_naive() - report.created_at).total_seconds() / 60)
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
    use_case = GetLatestAnalysisUseCase(
        db=db,
        current_user=current_user,
        analysis_repo=AnalysisRepository(db),
    )
    return await use_case.execute(ticker=ticker)


def _capsule_to_resp(cap):
    """Map a StockCapsule DB row to response dict, or None."""
    if cap is None:
        return None
    content = (cap.content or "").strip()
    if not content or content.startswith("**Error**") or content.lower().startswith("error:") or content.lower().startswith('{"error"'):
        return None
    return {
        "ticker": cap.ticker,
        "capsule_type": cap.capsule_type,
        "content": cap.content,
        "source_count": cap.source_count,
        "model_used": cap.model_used,
        "updated_at": cap.updated_at,
    }


@router.get("/{ticker}/capsule", response_model=StockCapsulesResponse)
async def get_stock_capsules(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return pre-computed news + fundamental capsules for a ticker."""
    use_case = GenerateStockCapsuleUseCase(db)
    capsules = await use_case.get_capsules(ticker)

    return {
        "ticker": ticker.upper(),
        "news": _capsule_to_resp(capsules.get("news")),
        "fundamental": _capsule_to_resp(capsules.get("fundamental")),
        "technical": _capsule_to_resp(capsules.get("technical")),
    }


@router.post("/{ticker}/capsule/refresh", response_model=StockCapsulesResponse)
async def refresh_stock_capsules(
    ticker: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    触发"全量研判"前的"数据预解构 (Capsules)"。

    【工程优化逻辑】
    AI 获取新闻和财务数据后直接生成简版胶囊报告：
    1. 强制刷新底层行情数据，确保数据时效性。
    2. 立即返回当前已有的胶囊（非阻塞响应），保持 UI 流畅。
    3. 利用 `BackgroundTasks` 在后台启动耗时的 AI 胶囊生成任务。
    这种二级缓存策略能够有效降低用户等待"最终研判报告"时的瞬时体感耗时。
    """
    ticker = ticker.upper().strip()

    # Step 1: Refresh market data (force=True fetches news, technicals, fundamentals fresh)
    # Cap at 60s so the AI capsule generation step still has time within the overall request budget.
    try:
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

    # Step 3: Schedule background regeneration
    background_tasks.add_task(
        _background_capsule_generation,
        ticker,
        current_user.preferred_ai_model,
        current_user.id,
    )

    return {
        "ticker": ticker.upper(),
        "news": _capsule_to_resp(existing_capsules.get("news")),
        "fundamental": _capsule_to_resp(existing_capsules.get("fundamental")),
        "technical": _capsule_to_resp(existing_capsules.get("technical")),
    }


async def _background_capsule_generation(
    ticker: str,
    preferred_model: Optional[str],
    user_id: Optional[str],
):
    """Background task to regenerate capsules after market data refresh."""
    async with SessionLocal() as db:
        try:
            ai = AIService(db=db)
            await ai._resolve_user(user_id)
            use_case = GenerateStockCapsuleUseCase(db, ai_service=ai)
            await use_case.generate_all(ticker, model=preferred_model)
            logger.info(f"[CapsuleRefresh] Background capsule generation completed for {ticker}")
        except Exception as exc:
            logger.error(f"[CapsuleRefresh] Background capsule generation failed for {ticker}: {exc}")
