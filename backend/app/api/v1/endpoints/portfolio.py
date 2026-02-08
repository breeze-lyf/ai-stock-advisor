from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
import asyncio
import logging

from app.core.database import get_db
from app.models.portfolio import Portfolio
from app.models.stock import Stock, MarketDataCache
from app.models.user import User
from app.api.deps import get_current_user
from app.services.market_data import MarketDataService
from app.schemas.portfolio import PortfolioItem, PortfolioCreate, SearchResult

logger = logging.getLogger(__name__)
logger.info("PHASE: Portfolio router module importing...")
router = APIRouter()

@router.get("/search", response_model=List[SearchResult])
async def search_stocks(query: str = "", remote: bool = False, db: AsyncSession = Depends(get_db)):
    """
    股票搜索接口
    - 同时支持本地数据库模糊搜索和远程 API 实时搜索
    - 如果本地没搜到且开启了 remote=True，会尝试从第三方源抓取并同步到本地
    """
    query = query.strip().upper()
    if not query:
        return []

    # 1. 本地搜索：根据代码或名称模糊匹配
    search_term = f"%{query}%"
    stmt = select(Stock).where(
        or_(
            Stock.ticker.ilike(search_term),
            Stock.name.ilike(search_term)
        )
    ).limit(10)
    
    result = await db.execute(stmt)
    stocks = result.scalars().all()
    
    # 2. 远程搜索：如果没有本地完全匹配的记录，且用户请求了远程搜索
    exact_match = any(s.ticker.upper() == query for s in stocks)
    
    if remote and not exact_match and len(query) <= 10:
        try:
            from app.services.market_providers import ProviderFactory
            provider = ProviderFactory.get_provider(query)
            
            # 获取实时报价以确认该股票代码有效
            quote = await provider.get_quote(query)
            
            if quote:
                # 如果代码有效但本地没有，则存入数据库，方便下次直接搜到
                stock_stmt = select(Stock).where(Stock.ticker == query)
                stock_result = await db.execute(stock_stmt)
                existing_stock = stock_result.scalar_one_or_none()
                
                if not existing_stock:
                    new_stock = Stock(ticker=query, name=quote.name or query)
                    db.add(new_stock)
                    new_cache = MarketDataCache(ticker=query, current_price=quote.price)
                    db.add(new_cache)
                    await db.commit()
                
                # 重新查询以便返回结果
                result = await db.execute(stmt)
                stocks = result.scalars().all()
        except Exception as e:
            logger.error(f"Remote search failed for {query}: {e}")

    return [SearchResult(ticker=s.ticker, name=s.name) for s in stocks]


@router.get("/", response_model=List[PortfolioItem])
async def get_portfolio(
    refresh: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的投资组合列表
    - 使用 outerjoin 一次性查出持仓量、最新价、基本面和技术指标
    - 如果 refresh=True，会触发后台并行更新所有持仓的实时行情
    """
    user_id = current_user.id

    # 1. 联表查询：Portfolio -> MarketDataCache -> Stock
    stmt = (
        select(Portfolio, MarketDataCache, Stock)
        .outerjoin(MarketDataCache, Portfolio.ticker == MarketDataCache.ticker)
        .outerjoin(Stock, Portfolio.ticker == Stock.ticker)
        .where(Portfolio.user_id == user_id)
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    # 2. 实时刷新逻辑
    if refresh:
        tickers = [p.ticker for p, _, _ in rows]
        if tickers:
            # 并行抓取行情，MarketDataService 会处理缓存和 DB 写入
            tasks = [
                MarketDataService.get_real_time_data(ticker, db, current_user.preferred_data_source)
                for ticker in tickers
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # 更新完后重新读取最新的数据库状态
            result = await db.execute(stmt)
            rows = result.all()

    # 3. 组织返回数据，计算未实现盈亏等指标
    items = []
    for p, m, s in rows:
        current_price = m.current_price if m else 0.0
        market_value = current_price * p.quantity
        unrealized_pl = (current_price - p.avg_cost) * p.quantity
        pl_percent = (unrealized_pl / (p.avg_cost * p.quantity)) * 100 if (p.avg_cost > 0 and p.quantity > 0) else 0
        
        items.append(PortfolioItem(
            ticker=p.ticker,
            name=s.name if s else p.ticker,
            quantity=p.quantity,
            avg_cost=p.avg_cost,
            current_price=current_price,
            market_value=market_value,
            unrealized_pl=unrealized_pl,
            pl_percent=pl_percent,
            last_updated=m.last_updated if m else None,
            # 基础面
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
            # 技术指标
            rsi_14=m.rsi_14 if m else None,
            ma_20=m.ma_20 if m else None,
            ma_50=m.ma_50 if m else None,
            ma_200=m.ma_200 if m else None,
            macd_val=m.macd_val if m else None,
            macd_signal=m.macd_signal if m else None,
            macd_hist=m.macd_hist if m else None,
            macd_hist_slope=m.macd_hist_slope if m else None,
            bb_upper=m.bb_upper if m else None,
            bb_middle=m.bb_middle if m else None,
            bb_lower=m.bb_lower if m else None,
            atr_14=m.atr_14 if m else None,
            k_line=m.k_line if m else None,
            d_line=m.d_line if m else None,
            j_line=m.j_line if m else None,
            volume_ma_20=m.volume_ma_20 if m else None,
            volume_ratio=m.volume_ratio if m else None,
            adx_14=m.adx_14 if m else None,
            pivot_point=m.pivot_point if m else None,
            resistance_1=m.resistance_1 if m else None,
            resistance_2=m.resistance_2 if m else None,
            support_1=m.support_1 if m else None,
            support_2=m.support_2 if m else None,
            change_percent=m.change_percent if m else 0.0
        ))
    return items

@router.post("/")
async def add_portfolio_item(
    item: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    添加或更新自选股/持仓
    """
    user_id = current_user.id
    ticker = item.ticker.upper().strip()
    
    # 检查是否已在持仓中
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
    
    # 异步更新：如果新股或是缺少数据，开启后台任务去抓取全量信息（不阻塞前端响应）
    cache_stmt = select(MarketDataCache).where(MarketDataCache.ticker == ticker)
    cache_result = await db.execute(cache_stmt)
    cache = cache_result.scalar_one_or_none()
    
    needs_fetch = not cache or cache.rsi_14 is None
    if needs_fetch:
        asyncio.create_task(_background_fetch(ticker, db))
    
    return {"message": "Portfolio updated"}

async def _background_fetch(ticker: str, db: AsyncSession):
    """后台任务：在添加股票后异步补全数据"""
    try:
        await MarketDataService.get_real_time_data(ticker, db, preferred_source="YFINANCE")
        logger.info(f"✅ Background fetch for {ticker} completed")
    except Exception as e:
        logger.error(f"❌ Background fetch for {ticker} failed: {e}")


        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")


@router.delete("/{ticker}")
async def delete_portfolio_item(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """从自选股中删除"""
    stmt = select(Portfolio).where(Portfolio.user_id == current_user.id, Portfolio.ticker == ticker)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    await db.delete(item)
    await db.commit()
    return {"message": "Item deleted"}

@router.post("/{ticker}/refresh")
async def refresh_stock_data(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """针对单个股票的手动强制刷新接口"""
    ticker = ticker.upper().strip()
    
    try:
        updated_cache = await MarketDataService.get_real_time_data(
            ticker, 
            db, 
            preferred_source=current_user.preferred_data_source,
            force_refresh=True
        )
        
        return {
            "ticker": ticker,
            "current_price": updated_cache.current_price,
            "change_percent": updated_cache.change_percent,
            "last_updated": updated_cache.last_updated
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")


@router.get("/{ticker}/news")
async def get_stock_news(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取该股票在数据库中存储的最新新闻"""
    from app.models.stock import StockNews
    ticker = ticker.upper().strip()
    
    stmt = (
        select(StockNews)
        .where(StockNews.ticker == ticker)
        .order_by(StockNews.publish_time.desc())
        .limit(20)
    )
    result = await db.execute(stmt)
    news = result.scalars().all()
    
    return [
        {
            "id": n.id,
            "title": n.title,
            "publisher": n.publisher,
            "link": n.link,
            "publish_time": n.publish_time,
            "summary": n.summary
        }
        for n in news
    ]
