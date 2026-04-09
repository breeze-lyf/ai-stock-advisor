"""
投资组合管理 API 端点 (Portfolio Management Endpoints)

职责：
- 提供持仓组合的 CRUD 操作接口
- 支持股票搜索、持仓刷新、重排序等功能
- 处理用户与投资组合相关的所有 HTTP 请求

主要端点：
- GET /search - 股票搜索（本地 + 远程）
- GET /summary - 获取组合汇总统计
- GET / - 获取持仓列表
- POST / - 添加持仓
- PATCH /{ticker} - 更新持仓信息
- DELETE /{ticker} - 删除持仓
- POST /{ticker}/refresh - 刷新个股数据
- GET /{ticker}/news - 获取个股新闻
- PATCH /reorder - 重排序持仓
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import get_db
from app.application.portfolio.manage_portfolio import (
    AddPortfolioItemUseCase,      # 添加持仓用例
    DeletePortfolioItemUseCase,   # 删除持仓用例
    RefreshPortfolioStockUseCase, # 刷新个股数据用例
    ReorderPortfolioUseCase,      # 重排序用例
)
from app.application.portfolio.search_engine import PortfolioSearchEngine
from app.application.portfolio.query_portfolio import GetPortfolioSummaryUseCase, GetPortfolioUseCase
from app.infrastructure.db.repositories.stock_repository import StockRepository
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.portfolio import PortfolioItem, PortfolioCreate, SearchResult, PortfolioSummary

logger = logging.getLogger(__name__)
logger.info("PHASE: Portfolio router module importing...")
router = APIRouter()


@router.get("/search", response_model=List[SearchResult])
async def search_stocks(
    query: str = "",
    remote: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    股票搜索接口

    功能：
    - 同时支持本地数据库模糊搜索和远程 API 实时搜索
    - 如果本地没搜到且开启了 remote=True，会尝试从第三方源抓取并同步到本地

    参数：
    - query: 搜索关键词（股票代码或名称）
    - remote: 是否启用远程搜索

    返回：
    - 搜索结果列表，包含股票代码和名称
    """
    query = query.strip().upper()
    if not query:
        return []
    repo = StockRepository(db)
    try:
        return await PortfolioSearchEngine(repo).search(
            query,
            preferred_source=current_user.preferred_data_source,
            remote=remote,
            limit=10,
        )
    except Exception as e:
        logger.error(f"Search failed for {query}: {e}", exc_info=True)
        return []


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取投资组合汇总统计

    返回数据包括：
    - 总市值 (total_market_value)
    - 累计盈亏 (total_unrealized_pl)
    - 累计盈亏百分比 (total_pl_percent)
    - 今日变动 (day_change)
    - 持仓列表 (holdings)
    - 行业分布 (sector_exposure)
    """
    return await GetPortfolioSummaryUseCase(db, current_user).execute()


@router.get("/", response_model=List[PortfolioItem])
async def get_portfolio(
    refresh: bool = False,
    price_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户持仓列表

    参数：
    - refresh: 是否刷新行情数据
    - price_only: 是否仅刷新价格（不获取技术指标）

    返回：
    - 持仓列表，包含每个持仓的详细信息
    """
    return await GetPortfolioUseCase(db, current_user).execute(refresh=refresh, price_only=price_only)


@router.post("/")
async def add_portfolio_item(
    item: PortfolioCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    添加新的持仓到投资组合

    功能：
    - 添加新持仓或更新已存在持仓的数量和成本
    - 后台异步抓取股票行情数据

    参数：
    - item: 持仓信息（股票代码、数量、成本价）
    - background_tasks: 后台任务队列，用于异步获取行情
    """
    return await AddPortfolioItemUseCase(db, current_user).execute(item, background_tasks)


class PortfolioUpdate(BaseModel):
    """
    更新持仓信息的请求模型

    属性：
    - quantity: 持仓数量（可选，不传则保持不变）
    - avg_cost: 持仓均价/成本价（可选，不传则保持不变）
    """
    quantity: Optional[float] = None
    avg_cost: Optional[float] = None


@router.patch("/{ticker}")
async def update_portfolio_item(
    ticker: str,
    update_data: PortfolioUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新持仓信息（数量/成本）

    功能：
    - 部分更新持仓记录
    - 只更新提供的字段，未提供的字段保持不变

    参数：
    - ticker: 股票代码（自动转为大写）
    - update_data: 更新数据（quantity 和/或 avg_cost）

    返回：
    - 成功消息和更新的股票代码

    异常：
    - 404: 如果持仓记录不存在
    """
    from app.infrastructure.db.repositories.portfolio_repository import PortfolioRepository

    repo = PortfolioRepository(db)
    item = await repo.get_portfolio_item(current_user.id, ticker.upper())

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # 更新字段（仅当提供了新值时）
    if update_data.quantity is not None:
        item.quantity = update_data.quantity
    if update_data.avg_cost is not None:
        item.avg_cost = update_data.avg_cost

    await repo.save_changes()

    return {"message": "Portfolio updated", "ticker": ticker.upper()}


@router.delete("/{ticker}")
async def delete_portfolio_item(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    从投资组合中删除持仓

    参数：
    - ticker: 要删除的股票代码

    返回：
    - 删除成功消息
    """
    return await DeletePortfolioItemUseCase(db, current_user).execute(ticker)


@router.post("/{ticker}/refresh")
async def refresh_stock_data(
    ticker: str,
    background_tasks: BackgroundTasks,
    price_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    刷新单只股票的行情数据

    功能：
    - 从数据源获取最新行情
    - 支持仅刷新价格模式（更快）或深度刷新（包含技术指标）
    - 后台异步同步数据到数据库

    参数：
    - ticker: 股票代码
    - background_tasks: 后台任务队列
    - price_only: 是否仅刷新价格

    返回：
    - 刷新结果（成功/失败状态、当前价格、涨跌幅等）
    """
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
    """
    获取指定股票在数据库中存储的最新新闻

    参数：
    - ticker: 股票代码

    返回：
    - 新闻列表，包含标题、发布者、链接、发布时间、摘要
    """
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
    orders: List[dict],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    重排序用户的持仓列表

    功能：
    - 批量更新持仓的排序顺序
    - 用于用户自定义持仓显示顺序

    参数：
    - orders: 排序列表，格式为 [{ticker: "AAPL", sort_order: 1}, ...]

    返回：
    - 重排序成功消息
    """
    return await ReorderPortfolioUseCase(db, current_user).execute(orders)
