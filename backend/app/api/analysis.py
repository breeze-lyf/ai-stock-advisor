from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.services.ai_service import AIService
from app.services.market_data import MarketDataService
from app.models.portfolio import Portfolio

router = APIRouter()

@router.post("/{ticker}")
async def analyze_stock(ticker: str, db: AsyncSession = Depends(get_db)):
    # 1. Fetch Market Data
    market_data_obj = await MarketDataService.get_real_time_data(ticker, db)
    
    # Convert object to dict for easier prompting
    if hasattr(market_data_obj, "__dict__"):
        market_data = {
            "current_price": market_data_obj.current_price,
            "change_percent": market_data_obj.change_percent,
            "rsi_14": market_data_obj.rsi_14,
            "market_status": market_data_obj.market_status
        }
    else:
        # Fallback dict from fallback logic
        market_data = {
            "current_price": market_data_obj.get("currentPrice"),
            "change_percent": market_data_obj.get("regularMarketChangePercent"),
            "rsi_14": 50.0, # Mock default
            "market_status": "OPEN"
        }

    # 2. Fetch User Portfolio (Context)
    # Hardcoded user for MVP
    user_id = "demo-user"
    stmt = select(Portfolio).where(Portfolio.user_id == user_id, Portfolio.ticker == ticker)
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

    # 3. Call AI
    ai_response = await AIService.generate_analysis(ticker, market_data, portfolio_data)

    return {
        "ticker": ticker,
        "analysis": ai_response,
        "sentiment": "NEUTRAL" # TODO: Parse from AI text if needed
    }
