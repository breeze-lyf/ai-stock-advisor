from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.services.ai_service import AIService
from app.services.market_data import MarketDataService
from app.models.portfolio import Portfolio
from app.models.user import User
from app.api.deps import get_current_user
from app.core import security

from app.schemas.analysis import AnalysisResponse

router = APIRouter()

@router.post("/{ticker}", response_model=AnalysisResponse)
async def analyze_stock(
    ticker: str, 
    force: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    股票分析接口 (核心业务逻辑)
    1. 检查用户权限/SaaS限制 (免费用户每日限额)
    2. 获取实时行情数据 (价格、技术指标)
    3. 获取相关新闻 (上下文)
    4. 获取用户持仓信息 (成本、盈亏)
    5. 调用 AI 模型生成投资建议
    """
    # 1. 检查限制 (SaaS 商业逻辑)
    # 如果用户没有配置自己的 Gemini API Key，则视为免费用户，受到每日使用次数限制
    if not current_user.api_key_gemini:
        # 免费层级限制检查
        from datetime import datetime
        from app.models.analysis import AnalysisReport
        from sqlalchemy import func
        
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 统计今日使用次数
        stmt = select(func.count()).select_from(AnalysisReport).where(
            AnalysisReport.user_id == current_user.id,
            AnalysisReport.created_at >= today_start
        )
        usage_count = await db.execute(stmt)
        count = usage_count.scalar_one()
        
        # 超过 3 次则拒绝请求
        if count >= 3:
            raise HTTPException(
                status_code=429, 
                detail="Free tier limit reached (3/day). Please add your own API Key in Settings for unlimited access."
            )

    # 2. 获取市场数据 (调用 MarketDataService)
    # 获取实时价格、涨跌幅、RSI/MACD/布林带等技术指标
    market_data_obj = await MarketDataService.get_real_time_data(ticker, db)
    
    # 将对象转换为字典，方便后续传给 AI Prompt
    if hasattr(market_data_obj, "__dict__"):
        market_data = {
            "current_price": market_data_obj.current_price,
            "change_percent": market_data_obj.change_percent,
            "rsi_14": market_data_obj.rsi_14,
            "ma_20": market_data_obj.ma_20,
            "ma_50": market_data_obj.ma_50,
            "ma_200": market_data_obj.ma_200,
            "macd_val": market_data_obj.macd_val,
            "macd_hist": market_data_obj.macd_hist,
            "bb_upper": market_data_obj.bb_upper,
            "bb_lower": market_data_obj.bb_lower,
            "kdj_k": market_data_obj.k_line,
            "atr_14": market_data_obj.atr_14,
            "market_status": market_data_obj.market_status
        }
    else:
        # 降级处理：如果获取对象失败，使用默认/回退数据
        market_data = {
            "current_price": market_data_obj.get("currentPrice"),
            "change_percent": market_data_obj.get("regularMarketChangePercent"),
            "rsi_14": 50.0,
            "market_status": "OPEN"
        }

    # 3. 获取新闻上下文
    # 查询该股票最近的 5 条新闻，帮助 AI 判断消息面
    from app.models.stock import StockNews
    news_stmt = select(StockNews).where(StockNews.ticker == ticker).order_by(StockNews.publish_time.desc()).limit(5)
    news_result = await db.execute(news_stmt)
    news_articles = news_result.scalars().all()
    news_data = [{"title": n.title, "publisher": n.publisher, "time": n.publish_time.isoformat()} for n in news_articles]

    # 4. 获取用户持仓 (个性化上下文)
    # 如果用户持有该股票，AI 会结合持仓成本给出建议 (如：是否止损/止盈)
    stmt = select(Portfolio).where(Portfolio.user_id == current_user.id, Portfolio.ticker == ticker)
    result = await db.execute(stmt)
    portfolio_item = result.scalar_one_or_none()
    
    portfolio_data = {}
    if portfolio_item:
        current_price = market_data['current_price'] or 0
        unrealized_pl = (current_price - portfolio_item.avg_cost) * portfolio_item.quantity
        pl_percent = (unrealized_pl / (portfolio_item.avg_cost * portfolio_item.quantity) * 100) if portfolio_item.avg_cost > 0 else 0
        
        portfolio_data = {
            "avg_cost": portfolio_item.avg_cost,
            "quantity": portfolio_item.quantity,
            "unrealized_pl": unrealized_pl,
            "pl_percent": pl_percent
        }

    # 5. 检查持久化缓存 (Persistence Cache)
    # 如果 force=False，则默认检索数据库中已有的最新分析报告
    from app.models.analysis import AnalysisReport
    
    preferred_model = current_user.preferred_ai_model or "gemini-1.5-flash"
    
    if not force:
        cache_stmt = select(AnalysisReport).where(
            AnalysisReport.user_id == current_user.id,
            AnalysisReport.ticker == ticker,
            AnalysisReport.model_used == preferred_model
        ).order_by(AnalysisReport.created_at.desc()).limit(1)
        
        cache_result = await db.execute(cache_stmt)
        cached_report = cache_result.scalar_one_or_none()
        
        if cached_report:
            logger.info(f"Returning latest report for {ticker} (model: {preferred_model})")
            return {
                "ticker": ticker,
                "analysis": cached_report.ai_response_markdown,
                "sentiment": cached_report.sentiment_score or "NEUTRAL",
                "is_cached": True,
                "model_used": cached_report.model_used,
                "created_at": cached_report.created_at
            }

    # 6. 调用 AI 服务生成分析报告
    # 解密用户 API Key (Gemini 是用户级的，SiliconFlow 是系统级或用户级)
    gemini_key = security.decrypt_api_key(current_user.api_key_gemini)
    siliconflow_key = security.decrypt_api_key(current_user.api_key_siliconflow)
    
    ai_response = await AIService.generate_analysis(
        ticker, 
        market_data, 
        portfolio_data,
        news_data,
        model=preferred_model,
        api_key_gemini=gemini_key,
        api_key_siliconflow=siliconflow_key
    )

    # 7. 持久化分析结果
    new_report = None
    try:
        new_report = AnalysisReport(
            user_id=current_user.id,
            ticker=ticker,
            model_used=preferred_model,
            ai_response_markdown=ai_response,
            input_context_snapshot={
                "market_data": market_data,
                "portfolio_data": portfolio_data
            }
        )
        db.add(new_report)
        await db.commit()
        await db.refresh(new_report)
    except Exception as e:
        logger.error(f"Failed to persist analysis report: {e}")
        await db.rollback()

    from datetime import datetime
    return {
        "ticker": ticker,
        "analysis": ai_response,
        "sentiment": "NEUTRAL",
        "is_cached": False,
        "model_used": preferred_model,
        "created_at": new_report.created_at if new_report else datetime.utcnow()
    }
@router.get("/{ticker}", response_model=AnalysisResponse)
async def get_latest_analysis(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取单支股票最新的分析记录（不触发新 AI 分析，仅查库）
    """
    from app.models.analysis import AnalysisReport
    
    preferred_model = current_user.preferred_ai_model or "gemini-1.5-flash"
    
    stmt = select(AnalysisReport).where(
        AnalysisReport.user_id == current_user.id,
        AnalysisReport.ticker == ticker,
        AnalysisReport.model_used == preferred_model
    ).order_by(AnalysisReport.created_at.desc()).limit(1)
    
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="No analysis found for this stock and model")
    
    return {
        "ticker": ticker,
        "analysis": report.ai_response_markdown,
        "sentiment": report.sentiment_score or "NEUTRAL",
        "is_cached": True,
        "model_used": report.model_used,
        "created_at": report.created_at
    }
