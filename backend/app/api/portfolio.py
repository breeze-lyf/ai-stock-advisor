from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.models.portfolio import Portfolio
from app.models.stock import Stock
from app.services.market_data import MarketDataService
from pydantic import BaseModel
from typing import List

router = APIRouter()

class PortfolioItem(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pl: float = 0.0
    pl_percent: float = 0.0

from app.models.user import User
from app.api.deps import get_current_user

# ... imports ...

@router.get("/", response_model=List[PortfolioItem])
async def get_portfolio(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id

    
    stmt = select(Portfolio).where(Portfolio.user_id == user_id)
    result = await db.execute(stmt)
    portfolios = result.scalars().all()
    
    items = []
    for p in portfolios:
        # Get market data
        market_data = await MarketDataService.get_real_time_data(p.ticker, db)
        
        # Handle dict (mock) vs object (cache)
        if isinstance(market_data, dict):
             current_price = market_data.get("currentPrice", 0)
        elif market_data:
             current_price = market_data.current_price
        else:
             current_price = 0

        market_value = current_price * p.quantity
        unrealized_pl = (current_price - p.avg_cost) * p.quantity
        pl_percent = (unrealized_pl / (p.avg_cost * p.quantity)) * 100 if p.avg_cost > 0 else 0
        
        items.append(PortfolioItem(
            ticker=p.ticker,
            quantity=p.quantity,
            avg_cost=p.avg_cost,
            current_price=current_price,
            market_value=market_value,
            unrealized_pl=unrealized_pl,
            pl_percent=pl_percent
        ))
    return items

class PortfolioCreate(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float

@router.post("/")
async def add_portfolio_item(
    item: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    
    # Check if stock exists or fetch it (to prime cache/stock table)
    await MarketDataService.get_real_time_data(item.ticker, db)
    
    # Check if exists
    stmt = select(Portfolio).where(Portfolio.user_id == user_id, Portfolio.ticker == item.ticker)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.quantity = item.quantity
        existing.avg_cost = item.avg_cost
    else:
        new_item = Portfolio(
            user_id=user_id,
            ticker=item.ticker,
            quantity=item.quantity,
            avg_cost=item.avg_cost
        )
        db.add(new_item)
    
    await db.commit()
    return {"message": "Portfolio updated"}
