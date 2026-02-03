from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.models.portfolio import Portfolio
from app.models.stock import Stock, MarketDataCache
import asyncio
from app.services.market_data import MarketDataService
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter()

from app.schemas.portfolio import PortfolioItem, PortfolioCreate, SearchResult

from app.models.user import User
from app.api.deps import get_current_user

# ... imports ...

# ... imports ...
from sqlalchemy import or_

# ... imports ...

@router.get("/search", response_model=List[SearchResult])
async def search_stocks(query: str = "", remote: bool = False, db: AsyncSession = Depends(get_db)):
    query = query.strip().upper()
    if not query:
        return []

    # 1. Local Search
    search_term = f"%{query}%"
    stmt = select(Stock).where(
        or_(
            Stock.ticker.ilike(search_term),
            Stock.name.ilike(search_term)
        )
    ).limit(10)
    
    result = await db.execute(stmt)
    stocks = result.scalars().all()
    
    # 2. Remote Search (Only if requested and no exact match found locally)
    exact_match = any(s.ticker.upper() == query for s in stocks)
    
    if remote and not exact_match and len(query) <= 10:
        try:
            # Quick yfinance check - just get stock info, don't calculate indicators
            import yfinance as yf
            import os
            loop = asyncio.get_event_loop()
            
            def quick_check():
                # Set proxy if configured
                if settings.HTTP_PROXY:
                    os.environ["HTTP_PROXY"] = settings.HTTP_PROXY
                    os.environ["HTTPS_PROXY"] = settings.HTTP_PROXY
                
                tick = yf.Ticker(query)
                info = tick.info
                if info and ('currentPrice' in info or 'regularMarketPrice' in info):
                    return {
                        "ticker": query,
                        "name": info.get('shortName', query),
                        "price": info.get('currentPrice') or info.get('regularMarketPrice')
                    }
                return None

            
            stock_info = await asyncio.wait_for(
                loop.run_in_executor(None, quick_check),
                timeout=5.0
            )
            
            if stock_info:
                # Create Stock entry if not exists
                stock_stmt = select(Stock).where(Stock.ticker == query)
                stock_result = await db.execute(stock_stmt)
                existing_stock = stock_result.scalar_one_or_none()
                
                if not existing_stock:
                    new_stock = Stock(ticker=query, name=stock_info["name"])
                    db.add(new_stock)
                    
                    # Also create a minimal cache entry
                    from app.models.stock import MarketDataCache
                    new_cache = MarketDataCache(ticker=query, current_price=stock_info["price"])
                    db.add(new_cache)
                    await db.commit()
                
                # Re-search locally to include the new one
                result = await db.execute(stmt)
                stocks = result.scalars().all()
        except Exception as e:
            print(f"Remote search failed for {query}: {e}")

    return [SearchResult(ticker=s.ticker, name=s.name) for s in stocks]


@router.get("/", response_model=List[PortfolioItem])
async def get_portfolio(
    refresh: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id

    # 1. First, get all portfolio items with their cached data in ONE query
    stmt = (
        select(Portfolio, MarketDataCache, Stock)
        .outerjoin(MarketDataCache, Portfolio.ticker == MarketDataCache.ticker)
        .outerjoin(Stock, Portfolio.ticker == Stock.ticker)
        .where(Portfolio.user_id == user_id)
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    # 2. If 'refresh' is requested, we update the data
    if refresh:
        tickers = [p.ticker for p, _, _ in rows]
        if tickers:
            # Update sequentially in SQLite to avoid session concurrency issues
            for ticker in tickers:
                await MarketDataService.get_real_time_data(ticker, db, current_user.preferred_data_source)
                # Add a small delay if using yfinance to avoid 429
                if current_user.preferred_data_source == "YFINANCE":
                    await asyncio.sleep(1)
            
            # Re-query to get the refreshed data
            result = await db.execute(stmt)
            rows = result.all()

    items = []
    for p, m, s in rows:
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
            pl_percent=pl_percent,
            last_updated=m.last_updated if m else None,
            # Fundamental
            sector=s.sector if s else None,
            industry=s.industry if s else None,
            market_cap=s.market_cap if s else None,
            pe_ratio=s.pe_ratio if s else None,
            forward_pe=s.forward_pe if s else None,
            eps=s.eps if s else None,
            dividend_yield=s.dividend_yield if s else None,
            beta=s.beta if s else None,
            fifty_two_week_high=s.fifty_two_week_high if s else None,
            fifty_two_week_low=s.fifty_two_week_low if s else None,
            # Tech
            rsi_14=m.rsi_14 if m else None,
            ma_20=m.ma_20 if m else None,
            ma_50=m.ma_50 if m else None,
            ma_200=m.ma_200 if m else None,
            macd_val=m.macd_val if m else None,
            macd_signal=m.macd_signal if m else None,
            macd_hist=m.macd_hist if m else None,
            bb_upper=m.bb_upper if m else None,
            bb_middle=m.bb_middle if m else None,
            bb_lower=m.bb_lower if m else None,
            atr_14=m.atr_14 if m else None,
            k_line=m.k_line if m else None,
            d_line=m.d_line if m else None,
            j_line=m.j_line if m else None,
            volume_ma_20=m.volume_ma_20 if m else None,
            volume_ratio=m.volume_ratio if m else None,
            change_percent=m.change_percent if m else 0.0
        ))
    return items

# ... class PortfolioCreate(BaseModel): ...

@router.post("/")
async def add_portfolio_item(
    item: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    ticker = item.ticker.upper().strip()
    
    # Check if exists in portfolio
    stmt = select(Portfolio).where(Portfolio.user_id == user_id, Portfolio.ticker == ticker)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.quantity = item.quantity
        existing.avg_cost = item.avg_cost
    else:
        new_item = Portfolio(
            user_id=user_id,
            ticker=ticker,
            quantity=item.quantity,
            avg_cost=item.avg_cost
        )
        db.add(new_item)
    
    await db.commit()
    
    # Auto-fetch data if stock is new OR cache is incomplete (missing technical indicators)
    cache_stmt = select(MarketDataCache).where(MarketDataCache.ticker == ticker)
    cache_result = await db.execute(cache_stmt)
    cache = cache_result.scalar_one_or_none()
    
    needs_fetch = not cache or cache.rsi_14 is None
    
    if needs_fetch:
        # Fetch in background (don't block the response)
        import asyncio
        asyncio.create_task(_background_fetch(ticker, db))
    
    return {"message": "Portfolio updated"}

async def _background_fetch(ticker: str, db: AsyncSession):
    try:
        await MarketDataService.get_real_time_data(ticker, db, preferred_source="YFINANCE")
        print(f"✅ Background fetch for {ticker} completed")
    except Exception as e:
        print(f"❌ Background fetch for {ticker} failed: {e}")


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
