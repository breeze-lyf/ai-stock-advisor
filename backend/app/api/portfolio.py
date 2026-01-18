from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.models.portfolio import Portfolio
from app.models.stock import Stock, MarketDataCache
import asyncio
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

# ... imports ...
from sqlalchemy import or_

class SearchResult(BaseModel):
    ticker: str
    name: str

@router.get("/search", response_model=List[SearchResult])
async def search_stocks(query: str = "", db: AsyncSession = Depends(get_db)):
    stmt = select(Stock)
    
    if query:
        search_term = f"%{query}%"
        stmt = stmt.where(
            or_(
                Stock.ticker.ilike(search_term),
                Stock.name.ilike(search_term)
            )
        )
    
    # Always limit to 10 to avoid huge payload
    stmt = stmt.limit(10)
    
    result = await db.execute(stmt)
    stocks = result.scalars().all()
    
    return [SearchResult(ticker=s.ticker, name=s.name) for s in stocks]

@router.get("/", response_model=List[PortfolioItem])
async def get_portfolio(
    refresh: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id

    # 1. First, get all portfolio items with their cached data in ONE query
    # This ensures the UI loads instantly from the database
    stmt = (
        select(Portfolio, MarketDataCache)
        .outerjoin(MarketDataCache, Portfolio.ticker == MarketDataCache.ticker)
        .where(Portfolio.user_id == user_id)
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    # 2. If 'refresh' is requested, we update the data concurrently
    # This is much faster than the old sequential loop
    if refresh:
        tickers = [p.ticker for p, _ in rows]
        if tickers:
            # Refresh all tickers concurrently
            tasks = [MarketDataService.get_real_time_data(t, db, current_user.preferred_data_source) for t in tickers]
            await asyncio.gather(*tasks)
            
            # Re-query to get the refreshed data
            result = await db.execute(stmt)
            rows = result.all()

    items = []
    for p, m in rows:
        # Data from cache (joined)
        current_price = m.current_price if m else 0.0
        
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
    
    # Speed up: Don't block adding a stock on a slow external network call
    # The prices will be updated by the next refresh cycle or a background task
    pass
    
    
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
@router.delete("/{ticker}")
async def delete_portfolio_item(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Portfolio).where(Portfolio.user_id == current_user.id, Portfolio.ticker == ticker)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    await db.delete(item)
    await db.commit()
    return {"message": "Item deleted"}
