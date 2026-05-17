"""
增强型 AI 分析 API
提供情景分析、多时间框架分析、风险因子分解等功能
"""
import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.domain.analysis.enhanced_ai_analysis import EnhancedAIAnalysisService
from app.services.market_data import MarketDataService
from app.services.macro_service import MacroService
from app.infrastructure.db.repositories.stock_repository import StockRepository
from app.infrastructure.db.repositories.market_data_repository import MarketDataRepository
from app.infrastructure.db.repositories.analysis_repository import AnalysisRepository
from app.services.ai_service import AIService
from app.application.analysis.analyze_stock import AnalyzeStockUseCase

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_market_data_dict(obj: Any) -> dict:
    return {
        "current_price": getattr(obj, "current_price", 0),
        "rsi_14": getattr(obj, "rsi_14", 50),
        "ma_20": getattr(obj, "ma_20", 0),
        "ma_50": getattr(obj, "ma_50", 0),
        "ma_200": getattr(obj, "ma_200", 0),
        "macd_val": getattr(obj, "macd_val", 0),
        "bb_upper": getattr(obj, "bb_upper", 0),
        "bb_lower": getattr(obj, "bb_lower", 0),
    }


def _build_fundamental_data(stock: Any) -> dict:
    if not stock:
        return {}
    return {
        "pe_ratio": getattr(stock, "pe_ratio", None),
        "forward_pe": getattr(stock, "forward_pe", None),
        "pb_ratio": getattr(stock, "pb_ratio", None),
        "roe": getattr(stock, "roe", None),
        "revenue_growth": getattr(stock, "revenue_growth", None),
        "earnings_growth": getattr(stock, "earnings_growth", None),
        "gross_margin": getattr(stock, "gross_margin", None),
        "industry": getattr(stock, "industry", "未知"),
        "sector": getattr(stock, "sector", "未知"),
        "beta": getattr(stock, "beta", 1.0),
    }


async def _gather_analysis_context(ticker: str, db: AsyncSession, user_id: str) -> dict:
    """Fetch market data, stock info, news, and macro context for a ticker."""
    market_data_obj = await MarketDataService.get_real_time_data(
        ticker, db, force_refresh=False, user_id=user_id
    )
    if not market_data_obj:
        raise HTTPException(status_code=404, detail=f"无法获取 {ticker} 的市场数据")

    market_data = _build_market_data_dict(market_data_obj)

    stock_repo = StockRepository(db)
    stock = await stock_repo.get_by_ticker(ticker)
    fundamental_data = _build_fundamental_data(stock)

    news_repo = MarketDataRepository(db)
    news_articles = await news_repo.get_latest_stock_news(ticker, limit=5)
    news_data = [
        {"title": n.title, "publisher": n.publisher, "time": n.publish_time.isoformat()}
        for n in news_articles
    ]

    macro_context = ""
    try:
        radar_topics = await MacroService.get_latest_radar(db)
        if radar_topics:
            macro_context = "### 宏观热点雷达:\n"
            for topic in radar_topics[:3]:
                macro_context += f"- **{topic.title}**: {topic.summary}\n"
    except Exception:
        pass

    return {
        "market_data_obj": market_data_obj,
        "market_data": market_data,
        "stock": stock,
        "fundamental_data": fundamental_data,
        "news_data": news_data,
        "macro_context": macro_context,
    }


@router.get("/{ticker}/scenario-analysis")
async def get_scenario_analysis(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticker = ticker.upper().strip()
    try:
        ctx = await _gather_analysis_context(ticker, db, current_user.id)

        scenario_result = await EnhancedAIAnalysisService.generate_scenario_analysis(
            ticker=ticker,
            market_data=ctx["market_data"],
            fundamental_data=ctx["fundamental_data"],
            news_data=ctx["news_data"],
            macro_context=ctx["macro_context"],
            db=db,
            user_id=current_user.id,
        )

        return {
            "ticker": ticker,
            "current_price": ctx["market_data"].get("current_price"),
            "scenario_analysis": scenario_result,
            "updated_at": None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scenario analysis failed for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{ticker}/risk-analysis")
async def get_risk_analysis(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticker = ticker.upper().strip()
    try:
        ctx = await _gather_analysis_context(ticker, db, current_user.id)

        risk_result = await EnhancedAIAnalysisService.analyze_risk_factors(
            ticker=ticker,
            market_data=ctx["market_data"],
            fundamental_data=ctx["fundamental_data"],
            db=db,
            user_id=current_user.id,
        )

        return {
            "ticker": ticker,
            "risk_analysis": risk_result,
            "updated_at": None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Risk analysis failed for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{ticker}/multi-timeframe")
async def get_multi_timeframe_analysis(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticker = ticker.upper().strip()
    try:
        ctx = await _gather_analysis_context(ticker, db, current_user.id)

        timeframe_result = await EnhancedAIAnalysisService.generate_multi_timeframe_analysis(
            ticker=ticker,
            market_data=ctx["market_data"],
            db=db,
            user_id=current_user.id,
        )

        return {
            "ticker": ticker,
            "current_price": ctx["market_data"].get("current_price"),
            "multi_timeframe_analysis": timeframe_result,
            "updated_at": None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multi-timeframe analysis failed for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{ticker}/enhanced-analysis")
async def get_enhanced_analysis(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ticker = ticker.upper().strip()
    try:
        ctx = await _gather_analysis_context(ticker, db, current_user.id)

        use_case = AnalyzeStockUseCase(
            analysis_repo=AnalysisRepository(db),
            ai_service=AIService(db=db, user=current_user),
            current_user=current_user,
            db=db,
        )
        base_analysis_task = use_case.execute(ticker, force=False)

        scenario_task = EnhancedAIAnalysisService.generate_scenario_analysis(
            ticker=ticker,
            market_data=ctx["market_data"],
            fundamental_data=ctx["fundamental_data"],
            news_data=ctx["news_data"],
            macro_context=ctx["macro_context"],
            db=db,
            user_id=current_user.id,
        )

        risk_task = EnhancedAIAnalysisService.analyze_risk_factors(
            ticker=ticker,
            market_data=ctx["market_data"],
            fundamental_data=ctx["fundamental_data"],
            db=db,
            user_id=current_user.id,
        )

        timeframe_task = EnhancedAIAnalysisService.generate_multi_timeframe_analysis(
            ticker=ticker,
            market_data=ctx["market_data"],
            db=db,
            user_id=current_user.id,
        )

        base_analysis, scenario_result, risk_result, timeframe_result = await asyncio.gather(
            base_analysis_task, scenario_task, risk_task, timeframe_task, return_exceptions=True
        )

        for name, result in [
            ("base", base_analysis), ("scenario", scenario_result),
            ("risk", risk_result), ("timeframe", timeframe_result),
        ]:
            if isinstance(result, Exception):
                logger.warning(f"{name} analysis for {ticker} failed: {result}")

        return {
            "ticker": ticker,
            "base_analysis": base_analysis if not isinstance(base_analysis, Exception) else {"error": str(base_analysis)},
            "scenario_analysis": scenario_result if not isinstance(scenario_result, Exception) else {"error": str(scenario_result)},
            "risk_analysis": risk_result if not isinstance(risk_result, Exception) else {"error": str(risk_result)},
            "multi_timeframe_analysis": timeframe_result if not isinstance(timeframe_result, Exception) else {"error": str(timeframe_result)},
            "updated_at": None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced analysis failed for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
