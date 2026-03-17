from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import get_db
from app.application.portfolio.manage_portfolio import (
    AddPortfolioItemUseCase,
    DeletePortfolioItemUseCase,
    RefreshPortfolioStockUseCase,
    ReorderPortfolioUseCase,
)
from app.application.portfolio.query_portfolio import GetPortfolioSummaryUseCase, GetPortfolioUseCase
from app.infrastructure.db.repositories.stock_repository import StockRepository
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.portfolio import PortfolioItem, PortfolioCreate, SearchResult, PortfolioSummary

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
    repo = StockRepository(db)

    stocks = await repo.search(query, limit=10)
    
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
                existing_stock = await repo.get_stock(query)
                
                if not existing_stock:
                    await repo.add_stock_with_cache(query, quote.name or query, quote.price)
                
                # 重新查询以便返回结果
                stocks = await repo.search(query, limit=10)
        except Exception as e:
            logger.error(f"Remote search failed for {query}: {e}")

    return [SearchResult(ticker=s.ticker, name=s.name) for s in stocks]



@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await GetPortfolioSummaryUseCase(db, current_user).execute()

@router.get("/", response_model=List[PortfolioItem])
async def get_portfolio(
    refresh: bool = False,
    price_only: bool = False, # 支持仅刷新价格模式
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await GetPortfolioUseCase(db, current_user).execute(refresh=refresh, price_only=price_only)

@router.post("/")
async def add_portfolio_item(
    item: PortfolioCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await AddPortfolioItemUseCase(db, current_user).execute(item, background_tasks)


@router.delete("/{ticker}")
async def delete_portfolio_item(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await DeletePortfolioItemUseCase(db, current_user).execute(ticker)

@router.post("/{ticker}/refresh")
async def refresh_stock_data(
    ticker: str,
    background_tasks: BackgroundTasks,
    price_only: bool = False, # 支持仅刷新价格模式
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await RefreshPortfolioStockUseCase(db, current_user).execute(
        ticker=ticker,
        background_tasks=background_tasks,
        price_only=price_only,
    )


@router.get("/{ticker}/news")
async def get_stock_news(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取该股票在数据库中存储的最新新闻"""
    ticker = ticker.upper().strip()
    news = await StockRepository(db).get_latest_news(ticker, limit=20)
    
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
@router.patch("/reorder")
async def reorder_portfolio(
    orders: List[dict], # [{ticker: "AAPL", sort_order: 1}, ...]
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await ReorderPortfolioUseCase(db, current_user).execute(orders)
