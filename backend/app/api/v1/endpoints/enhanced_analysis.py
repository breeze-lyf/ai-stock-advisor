"""
增强型 AI 分析 API
提供情景分析、多时间框架分析、风险因子分解等功能
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.enhanced_ai_analysis import EnhancedAIAnalysisService
from app.services.market_data import MarketDataService
from app.application.analysis.analyze_stock import AnalyzeStockUseCase

router = APIRouter()


@router.get("/{ticker}/scenario-analysis")
async def get_scenario_analysis(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取情景分析（乐观/基准/悲观）

    返回三种不同情景下的目标价、涨跌空间和核心驱动因素
    """
    ticker = ticker.upper().strip()

    try:
        # 获取市场数据
        market_data_obj = await MarketDataService.get_real_time_data(
            ticker, db, force_refresh=False, user_id=current_user.id
        )

        if not market_data_obj:
            raise HTTPException(
                status_code=404,
                detail=f"无法获取 {ticker} 的市场数据"
            )

        # 构建市场数据字典
        market_data = {
            "current_price": getattr(market_data_obj, "current_price", 0),
            "rsi_14": getattr(market_data_obj, "rsi_14", 50),
            "ma_20": getattr(market_data_obj, "ma_20", 0),
            "ma_50": getattr(market_data_obj, "ma_50", 0),
            "ma_200": getattr(market_data_obj, "ma_200", 0),
            "macd_val": getattr(market_data_obj, "macd_val", 0),
            "bb_upper": getattr(market_data_obj, "bb_upper", 0),
            "bb_lower": getattr(market_data_obj, "bb_lower", 0),
        }

        # 获取基本面数据
        from app.infrastructure.db.repositories.stock_repository import StockRepository
        stock_repo = StockRepository(db)
        stock = await stock_repo.get_by_ticker(ticker)

        fundamental_data = {}
        if stock:
            fundamental_data = {
                "pe_ratio": getattr(stock, "pe_ratio", None),
                "forward_pe": getattr(stock, "forward_pe", None),
                "pb_ratio": getattr(stock, "pb_ratio", None),
                "roe": getattr(stock, "roe", None),
                "revenue_growth": getattr(stock, "revenue_growth", None),
                "earnings_growth": getattr(stock, "earnings_growth", None),
                "gross_margin": getattr(stock, "gross_margin", None),
                "industry": getattr(stock, "industry", "未知"),
                "sector": getattr(stock, "sector", "未知"),
            }

        # 获取新闻数据
        from app.infrastructure.db.repositories.market_data_repository import MarketDataRepository
        news_repo = MarketDataRepository(db)
        news_articles = await news_repo.get_latest_stock_news(ticker, limit=5)
        news_data = [
            {"title": n.title, "publisher": n.publisher, "time": n.publish_time.isoformat()}
            for n in news_articles
        ]

        # 获取宏观上下文
        from app.services.macro_service import MacroService
        macro_context = ""
        try:
            radar_topics = await MacroService.get_latest_radar(db)
            if radar_topics:
                macro_context = "### 宏观热点雷达:\n"
                for topic in radar_topics[:3]:
                    macro_context += f"- **{topic.title}**: {topic.summary}\n"
        except Exception:
            pass

        # 调用增强分析服务
        scenario_result = await EnhancedAIAnalysisService.generate_scenario_analysis(
            ticker=ticker,
            market_data=market_data,
            fundamental_data=fundamental_data,
            news_data=news_data,
            macro_context=macro_context,
            db=db,
            user_id=current_user.id,
        )

        return {
            "ticker": ticker,
            "current_price": market_data.get("current_price"),
            "scenario_analysis": scenario_result,
            "updated_at": market_data.get("updated_at"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"情景分析生成失败：{str(e)[:200]}"
        )


@router.get("/{ticker}/risk-analysis")
async def get_risk_analysis(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取风险因子分析

    返回市场风险、行业风险、公司特定风险等评估
    """
    ticker = ticker.upper().strip()

    try:
        # 获取市场数据
        market_data_obj = await MarketDataService.get_real_time_data(
            ticker, db, force_refresh=False, user_id=current_user.id
        )

        if not market_data_obj:
            raise HTTPException(
                status_code=404,
                detail=f"无法获取 {ticker} 的市场数据"
            )

        market_data = {
            "current_price": getattr(market_data_obj, "current_price", 0),
            "rsi_14": getattr(market_data_obj, "rsi_14", 50),
        }

        # 获取基本面数据
        from app.infrastructure.db.repositories.stock_repository import StockRepository
        stock_repo = StockRepository(db)
        stock = await stock_repo.get_by_ticker(ticker)

        fundamental_data = {}
        if stock:
            fundamental_data = {
                "beta": getattr(stock, "beta", 1.0),
                "industry": getattr(stock, "industry", "未知"),
                "sector": getattr(stock, "sector", "未知"),
            }

        # 调用风险分析服务
        risk_result = await EnhancedAIAnalysisService.analyze_risk_factors(
            ticker=ticker,
            market_data=market_data,
            fundamental_data=fundamental_data,
            db=db,
            user_id=current_user.id,
        )

        return {
            "ticker": ticker,
            "risk_analysis": risk_result,
            "updated_at": market_data.get("updated_at"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"风险分析生成失败：{str(e)[:200]}"
        )


@router.get("/{ticker}/multi-timeframe")
async def get_multi_timeframe_analysis(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取多时间框架分析

    返回短线（1-5 日）、中线（1-4 周）、长线（3-12 月）的趋势判断
    """
    ticker = ticker.upper().strip()

    try:
        # 获取市场数据
        market_data_obj = await MarketDataService.get_real_time_data(
            ticker, db, force_refresh=False, user_id=current_user.id
        )

        if not market_data_obj:
            raise HTTPException(
                status_code=404,
                detail=f"无法获取 {ticker} 的市场数据"
            )

        market_data = {
            "current_price": getattr(market_data_obj, "current_price", 0),
            "ma_20": getattr(market_data_obj, "ma_20", 0),
            "ma_50": getattr(market_data_obj, "ma_50", 0),
            "ma_200": getattr(market_data_obj, "ma_200", 0),
        }

        # 调用多时间框架分析服务
        timeframe_result = await EnhancedAIAnalysisService.generate_multi_timeframe_analysis(
            ticker=ticker,
            market_data=market_data,
            db=db,
            user_id=current_user.id,
        )

        return {
            "ticker": ticker,
            "current_price": market_data.get("current_price"),
            "multi_timeframe_analysis": timeframe_result,
            "updated_at": market_data.get("updated_at"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"多时间框架分析生成失败：{str(e)[:200]}"
        )


@router.get("/{ticker}/enhanced-analysis")
async def get_enhanced_analysis(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取完整的增强型 AI 分析

    包含：
    - 基础 AI 分析
    - 情景分析
    - 风险分析
    - 多时间框架分析
    """
    ticker = ticker.upper().strip()

    try:
        # 并行获取所有分析
        import asyncio

        # 基础分析
        use_case = AnalyzeStockUseCase(db, current_user)
        base_analysis_task = use_case.execute(ticker, force=False)

        # 获取市场数据用于其他分析
        market_data_obj = await MarketDataService.get_real_time_data(
            ticker, db, force_refresh=False, user_id=current_user.id
        )

        if not market_data_obj:
            raise HTTPException(
                status_code=404,
                detail=f"无法获取 {ticker} 的市场数据"
            )

        market_data = {
            "current_price": getattr(market_data_obj, "current_price", 0),
            "rsi_14": getattr(market_data_obj, "rsi_14", 50),
            "ma_20": getattr(market_data_obj, "ma_20", 0),
            "ma_50": getattr(market_data_obj, "ma_50", 0),
            "ma_200": getattr(market_data_obj, "ma_200", 0),
            "macd_val": getattr(market_data_obj, "macd_val", 0),
            "bb_upper": getattr(market_data_obj, "bb_upper", 0),
            "bb_lower": getattr(market_data_obj, "bb_lower", 0),
        }

        # 获取基本面数据
        from app.infrastructure.db.repositories.stock_repository import StockRepository
        stock_repo = StockRepository(db)
        stock = await stock_repo.get_by_ticker(ticker)

        fundamental_data = {}
        if stock:
            fundamental_data = {
                "beta": getattr(stock, "beta", 1.0),
                "industry": getattr(stock, "industry", "未知"),
            }

        # 并行执行增强分析
        scenario_task = EnhancedAIAnalysisService.generate_scenario_analysis(
            ticker=ticker,
            market_data=market_data,
            fundamental_data={"beta": 1.0},
            news_data=[],
            macro_context="",
            db=db,
            user_id=current_user.id,
        )

        risk_task = EnhancedAIAnalysisService.analyze_risk_factors(
            ticker=ticker,
            market_data=market_data,
            fundamental_data=fundamental_data,
            db=db,
            user_id=current_user.id,
        )

        timeframe_task = EnhancedAIAnalysisService.generate_multi_timeframe_analysis(
            ticker=ticker,
            market_data=market_data,
            db=db,
            user_id=current_user.id,
        )

        # 等待所有任务完成
        base_analysis, scenario_result, risk_result, timeframe_result = await asyncio.gather(
            base_analysis_task,
            scenario_task,
            risk_task,
            timeframe_task,
            return_exceptions=True
        )

        # 处理异常
        if isinstance(base_analysis, Exception):
            base_analysis = {"error": str(base_analysis)}
        if isinstance(scenario_result, Exception):
            scenario_result = {"error": str(scenario_result)}
        if isinstance(risk_result, Exception):
            risk_result = {"error": str(risk_result)}
        if isinstance(timeframe_result, Exception):
            timeframe_result = {"error": str(timeframe_result)}

        return {
            "ticker": ticker,
            "base_analysis": base_analysis,
            "scenario_analysis": scenario_result,
            "risk_analysis": risk_result,
            "multi_timeframe_analysis": timeframe_result,
            "updated_at": market_data.get("updated_at"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"增强分析生成失败：{str(e)[:200]}"
        )
