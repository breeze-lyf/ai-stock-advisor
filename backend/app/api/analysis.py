from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.services.ai_service import AIService
from app.services.market_data import MarketDataService
from app.models.portfolio import Portfolio
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/{ticker}")
async def analyze_stock(
    ticker: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Check Limits (SaaS Logic)
    if not current_user.api_key_gemini:
        # Free Tier Limit Check
        from datetime import datetime
        from app.models.analysis import AnalysisReport
        from sqlalchemy import func
        
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Count usage today
        stmt = select(func.count()).select_from(AnalysisReport).where(
            AnalysisReport.user_id == current_user.id,
            AnalysisReport.created_at >= today_start
        )
        usage_count = await db.execute(stmt)
        count = usage_count.scalar_one()
        
        if count >= 3:
            raise HTTPException(
                status_code=429, 
                detail="Free tier limit reached (3/day). Please add your own API Key in Settings for unlimited access."
            )

    # 2. Fetch Market Data
    market_data_obj = await MarketDataService.get_real_time_data(ticker, db)
    
    # Convert object to dict for easier prompting
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
        # Fallback dict from fallback logic
        market_data = {
            "current_price": market_data_obj.get("currentPrice"),
            "change_percent": market_data_obj.get("regularMarketChangePercent"),
            "rsi_14": 50.0,
            "market_status": "OPEN"
        }

    # 3. Fetch News Context
    from app.models.stock import StockNews
    news_stmt = select(StockNews).where(StockNews.ticker == ticker).order_by(StockNews.publish_time.desc()).limit(5)
    news_result = await db.execute(news_stmt)
    news_articles = news_result.scalars().all()
    news_data = [{"title": n.title, "publisher": n.publisher, "time": n.publish_time.isoformat()} for n in news_articles]

    # 2. Fetch User Portfolio (Context)
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

    # 3. Call AI (Pass User Key)
    ai_response = await AIService.generate_analysis(
        ticker, 
        market_data, 
        portfolio_data,
        news_data,
        api_key=current_user.api_key_gemini
    )

    return {
        "ticker": ticker,
        "analysis": ai_response,
        "sentiment": "NEUTRAL" # TODO: Parse from AI text if needed
    }
