import logging
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

logger = logging.getLogger(__name__)

router = APIRouter()

def extract_entry_prices_fallback(action_advice: str) -> tuple[Optional[float], Optional[float]]:
    """兜底逻辑：从建议文本中提取数字区间 [low, high]"""
    if not action_advice:
        return None, None
    import re
    # 搜索形如 "45.10-46.20" 或 "45.10至46.20" 的价格区间
    zone_match = re.search(r"(\d+\.?\d*)\s*(?:-|至|~)\s*(\d+\.?\d*)", action_advice)
    if zone_match:
        vals = sorted([float(zone_match.group(1)), float(zone_match.group(2))])
        return vals[0], vals[1]
    # 搜索形如 "45.10 附近" 或 "建仓位 45.10" 或 "50.00左右"
    # 增加对数字在前的匹配，如 "50.00附近"
    price_match = re.search(r"(?:附近|点位|位|价|在|于)\s*(\d+\.?\d*)|(\d+\.?\d*)\s*(?:元)?\s*(?:附近|左右|点位)", action_advice)
    if price_match:
        # group(1) 是前缀匹配到的数字，group(2) 是后缀匹配到的数字
        val_str = price_match.group(1) or price_match.group(2)
        val = float(val_str)
        return val, val
    return None, None

def extract_entry_zone_fallback(action_advice: str) -> Optional[str]:
    """旧格式兜底：返回字符串描述"""
    low, high = extract_entry_prices_fallback(action_advice)
    if low and high:
        if low == high:
            return f"Near {low}"
        return f"{low} - {high}"
    return None

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
    from app.models.stock import Stock
    stock_stmt = select(Stock).where(Stock.ticker == ticker)
    stock_result = await db.execute(stock_stmt)
    stock_obj = stock_result.scalar_one_or_none()
    
    # 获取实时价格、涨跌幅、RSI/MACD/布林带等技术指标
    market_data_obj = await MarketDataService.get_real_time_data(ticker, db, force_refresh=force)
    
    # 将对象转换为字典，方便后续传给 AI Prompt
    if hasattr(market_data_obj, "__dict__"):
        market_data = {
            "current_price": round(market_data_obj.current_price, 2) if market_data_obj.current_price else None,
            "change_percent": round(market_data_obj.change_percent, 2) if market_data_obj.change_percent else None,
            "rsi_14": round(market_data_obj.rsi_14, 2) if market_data_obj.rsi_14 else None,
            "ma_20": round(market_data_obj.ma_20, 2) if market_data_obj.ma_20 else None,
            "ma_50": round(market_data_obj.ma_50, 2) if market_data_obj.ma_50 else None,
            "ma_200": round(market_data_obj.ma_200, 2) if market_data_obj.ma_200 else None,
            "macd_val": round(market_data_obj.macd_val, 2) if market_data_obj.macd_val else None,
            "macd_hist": round(market_data_obj.macd_hist, 2) if market_data_obj.macd_hist else None,
            "bb_upper": round(market_data_obj.bb_upper, 2) if market_data_obj.bb_upper else None,
            "bb_lower": round(market_data_obj.bb_lower, 2) if market_data_obj.bb_lower else None,
            "kdj_k": round(market_data_obj.k_line, 2) if market_data_obj.k_line else None,
            "atr_14": round(market_data_obj.atr_14, 2) if market_data_obj.atr_14 else None,
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
        pl_percent = (unrealized_pl / (portfolio_item.avg_cost * portfolio_item.quantity) * 100) if (portfolio_item.avg_cost > 0 and portfolio_item.quantity > 0) else 0
        
        portfolio_data = {
            "avg_cost": portfolio_item.avg_cost,
            "quantity": portfolio_item.quantity,
            "unrealized_pl": unrealized_pl,
            "pl_percent": pl_percent
        }

    # 4.5 汇总基础面数据 (Fundamental Context)
    fundamental_data = {}
    if stock_obj:
        fundamental_data = {
            "sector": stock_obj.sector,
            "industry": stock_obj.industry,
            "market_cap": stock_obj.market_cap,
            "pe_ratio": round(stock_obj.pe_ratio, 2) if stock_obj.pe_ratio else None,
            "forward_pe": round(stock_obj.forward_pe, 2) if stock_obj.forward_pe else None,
            "eps": round(stock_obj.eps, 2) if stock_obj.eps else None,
            "dividend_yield": round(stock_obj.dividend_yield, 2) if stock_obj.dividend_yield else None,
            "beta": round(stock_obj.beta, 2) if stock_obj.beta else None,
            "fifty_two_week_high": round(stock_obj.fifty_two_week_high, 2) if stock_obj.fifty_two_week_high else None,
            "fifty_two_week_low": round(stock_obj.fifty_two_week_low, 2) if stock_obj.fifty_two_week_low else None
        }

    # 5. 检查持久化缓存 (Persistence Cache)
    # 如果 force=False，则默认检索数据库中已有的最新分析报告
    from app.models.analysis import AnalysisReport
    
    # 调试日志：查看传给 AI 的原始数据状态
    logger.info(f"Preparing AI analysis for {ticker}. Market Data keys present: {list(market_data.keys())}")
    if not market_data.get('rsi_14'):
        logger.warning(f"Technical indicators missing for {ticker}, prompt may be low quality.")
    
    preferred_model = current_user.preferred_ai_model or "gemini-1.5-flash"
    
    if not force:
        cache_stmt = select(AnalysisReport).where(
            AnalysisReport.user_id == current_user.id,
            AnalysisReport.ticker == ticker,
            AnalysisReport.model_used == preferred_model
        ).order_by(AnalysisReport.created_at.desc()).limit(1)
        
        cache_result = await db.execute(cache_stmt)
        cached_report = cache_result.scalar_one_or_none()
        
        if cached_report and cached_report.technical_analysis:
            # 补全历史数据的数值字段
            if cached_report.entry_price_low is None and cached_report.entry_price_high is None:
                cached_report.entry_price_low, cached_report.entry_price_high = extract_entry_prices_fallback(cached_report.action_advice)
            
            logger.info(f"Returning latest report for {ticker} (model: {preferred_model})")
            return {
                "ticker": ticker,
                "analysis": cached_report.ai_response_markdown,
                "sentiment_score": float(cached_report.sentiment_score) if cached_report.sentiment_score else None,
                "summary_status": cached_report.summary_status,
                "risk_level": cached_report.risk_level,
                "technical_analysis": cached_report.technical_analysis,
                "fundamental_news": cached_report.fundamental_news,
                "action_advice": cached_report.action_advice,
                "investment_horizon": cached_report.investment_horizon,
                "confidence_level": cached_report.confidence_level,
                "immediate_action": cached_report.immediate_action,
                "target_price": cached_report.target_price,
                "stop_loss_price": cached_report.stop_loss_price,
                "entry_zone": cached_report.entry_zone or extract_entry_zone_fallback(cached_report.action_advice),
                "entry_price_low": cached_report.entry_price_low,
                "entry_price_high": cached_report.entry_price_high,
                "rr_ratio": cached_report.rr_ratio,
                "is_cached": True,
                "model_used": cached_report.model_used,
                "created_at": cached_report.created_at
            }

    # 6. 调用 AI 服务生成分析报告 (要求 JSON 返回)
    gemini_key = security.decrypt_api_key(current_user.api_key_gemini)
    siliconflow_key = security.decrypt_api_key(current_user.api_key_siliconflow)
    
    ai_raw_response = await AIService.generate_analysis(
        ticker, 
        market_data, 
        portfolio_data,
        news_data,
        fundamental_data=fundamental_data,
        model=preferred_model,
        api_key_gemini=gemini_key,
        api_key_siliconflow=siliconflow_key
    )
    
    # 记录 Prompt 日志
    # 记录完整 Response 日志
    logger.info(f"AI Response for {ticker}: {ai_raw_response}")

    # 7. 解析结构化 JSON 结果
    import json
    parsed_data = {}
    # --- 增强型 JSON 解析逻辑 ---
    ai_raw_response = ai_raw_response.strip()
    parsed_data = {}
    
    # 1. 检查是否是 AIService 返回的显式错误字符串
    if ai_raw_response.startswith("**Error**"):
        logger.error(f"AI Service returned an error: {ai_raw_response}")
        parsed_data = {
            "technical_analysis": f"AI 服务调用异常: {ai_raw_response}",
            "action_advice": "由于 AI 接口调用失败，暂时无法生成详细诊断建议。请检查 API 配置或稍后重试。",
            "summary_status": "调用失败",
            "sentiment_score": 50,
            "risk_level": "未知"
        }
    else:
        try:
            # 2. 尝试正则提取第一个 { 到最后一个 } 之间的内容 (处理前后杂质)
            import re
            json_match = re.search(r'(\{.*\})', ai_raw_response, re.DOTALL)
            if json_match:
                clean_json = json_match.group(1)
                parsed_data = json.loads(clean_json)
            else:
                # 3. 兜底解析
                clean_json = ai_raw_response.replace("```json", "").replace("```", "").strip()
                parsed_data = json.loads(clean_json)
        except Exception as e:
            logger.error(f"Failed to parse AI JSON response: {e}. Raw: {ai_raw_response[:200]}...")
            # 严重降级处理：尝试把原始文本塞入主要说明字段，防止前端全空
            parsed_data = {
                "technical_analysis": ai_raw_response if len(ai_raw_response) > 50 else "",
                "action_advice": ai_raw_response if len(ai_raw_response) <= 50 else "AI 响应格式解析失败，请查看技术分析详情。",
                "summary_status": "解析失败",
                "sentiment_score": 50,
                "risk_level": "中"
            }

    def to_str(val):
        if val is None: return None
        if isinstance(val, (list, dict)): 
            try:
                return "\n".join(str(item) for item in val) if isinstance(val, list) else str(val)
            except:
                return str(val)
        return str(val)

    def to_float(val):
        try:
            if val is None or val == "": return None
            return float(val)
        except (ValueError, TypeError):
            return None

    # 8. 持久化分析结果 (存入独立字段)
    new_report = None
    try:
        new_report = AnalysisReport(
            user_id=current_user.id,
            ticker=ticker,
            model_used=preferred_model,
            ai_response_markdown=ai_raw_response, # 保留原始全文
            sentiment_score=to_str(parsed_data.get("sentiment_score")),
            summary_status=to_str(parsed_data.get("summary_status")),
            risk_level=to_str(parsed_data.get("risk_level")),
            technical_analysis=to_str(parsed_data.get("technical_analysis")),
            fundamental_news=to_str(parsed_data.get("fundamental_news")),
            confidence_level=to_float(parsed_data.get("confidence_level")),
            immediate_action=to_str(parsed_data.get("immediate_action")),
            action_advice=to_str(parsed_data.get("action_advice")),
            investment_horizon=to_str(parsed_data.get("investment_horizon")),
            target_price=to_float(parsed_data.get("target_price")),
            stop_loss_price=to_float(parsed_data.get("stop_loss_price")),
            entry_zone=to_str(parsed_data.get("entry_zone")),
            entry_price_low=to_float(parsed_data.get("entry_price_low")),
            entry_price_high=to_float(parsed_data.get("entry_price_high")),
            rr_ratio=to_str(parsed_data.get("rr_ratio")),
            input_context_snapshot={
                "market_data": market_data,
                "portfolio_data": portfolio_data
            }
        )
        
        # 兜底逻辑：如果数值字段为空，尝试从文本提取
        if new_report.entry_price_low is None and new_report.entry_price_high is None:
            new_report.entry_price_low, new_report.entry_price_high = extract_entry_prices_fallback(new_report.action_advice)
        
        if not new_report.entry_zone:
            new_report.entry_zone = extract_entry_zone_fallback(new_report.action_advice)
        db.add(new_report)

        await db.commit()
        await db.refresh(new_report)
    except Exception as e:
        logger.error(f"Failed to persist structured analysis report: {e}")
        await db.rollback()

    from datetime import datetime
    return {
        "ticker": ticker,
        "sentiment_score": to_float(parsed_data.get("sentiment_score")),
        "summary_status": to_str(parsed_data.get("summary_status")),
        "risk_level": to_str(parsed_data.get("risk_level")),
        "technical_analysis": to_str(parsed_data.get("technical_analysis")),
        "fundamental_news": to_str(parsed_data.get("fundamental_news")),
        "action_advice": to_str(parsed_data.get("action_advice")),
        "investment_horizon": to_str(parsed_data.get("investment_horizon")),
        "confidence_level": to_float(parsed_data.get("confidence_level")),
        "immediate_action": to_str(parsed_data.get("immediate_action")),
        "target_price": to_float(parsed_data.get("target_price")),
        "stop_loss_price": to_float(parsed_data.get("stop_loss_price")),
        "entry_zone": new_report.entry_zone if new_report else to_str(parsed_data.get("entry_zone")),
        "entry_price_low": new_report.entry_price_low if new_report else to_float(parsed_data.get("entry_price_low")),
        "entry_price_high": new_report.entry_price_high if new_report else to_float(parsed_data.get("entry_price_high")),
        "rr_ratio": to_str(parsed_data.get("rr_ratio")),
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
        "sentiment_score": float(report.sentiment_score) if report.sentiment_score else None,
        "summary_status": report.summary_status,
        "risk_level": report.risk_level,
        "technical_analysis": report.technical_analysis,
        "fundamental_news": report.fundamental_news,
        "action_advice": report.action_advice,
        "investment_horizon": report.investment_horizon,
        "confidence_level": report.confidence_level,
        "immediate_action": report.immediate_action,
        "target_price": report.target_price,
        "stop_loss_price": report.stop_loss_price,
        "entry_zone": report.entry_zone or extract_entry_zone_fallback(report.action_advice),
        "entry_price_low": report.entry_price_low if report.entry_price_low is not None else extract_entry_prices_fallback(report.action_advice)[0],
        "entry_price_high": report.entry_price_high if report.entry_price_high is not None else extract_entry_prices_fallback(report.action_advice)[1],
        "rr_ratio": report.rr_ratio,
        "is_cached": True,
        "model_used": report.model_used,
        "created_at": report.created_at
    }
