from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import logging

from app.core.database import get_db
from app.models.trade import SimulatedTrade, TradeHistoryLog, TradeStatus
from app.models.stock import Stock
from app.models.user import User
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/")
async def create_simulated_trade(
    ticker: str,
    entry_price: float,
    entry_reason: str,
    target_price: Optional[float] = None,
    stop_loss_price: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    一键加入模拟盘 (Join Paper Trading)
    """
    ticker = ticker.upper().strip()
    
    # Check if stock exists in db
    stmt = select(Stock).where(Stock.ticker == ticker)
    result = await db.execute(stmt)
    stock = result.scalar_one_or_none()
    
    if not stock:
         raise HTTPException(status_code=404, detail="Stock not found in database. Search for it first.")
         
    new_trade = SimulatedTrade(
        user_id=current_user.id,
        ticker=ticker,
        entry_price=entry_price,
        entry_reason=entry_reason,
        target_price=target_price,
        stop_loss_price=stop_loss_price,
        current_price=entry_price,
        unrealized_pnl_pct=0.0,
        status=TradeStatus.OPEN
    )
    
    db.add(new_trade)
    await db.commit()
    await db.refresh(new_trade)
    
    return {"message": "Successfully joined paper trading", "trade_id": new_trade.id}


@router.get("/")
async def get_simulated_trades(
    status: Optional[TradeStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取所有的模拟交易 (Get all simulated trades)
    """
    stmt = select(SimulatedTrade).where(SimulatedTrade.user_id == current_user.id)
    if status is not None:
        stmt = stmt.where(SimulatedTrade.status == status)
        
    stmt = stmt.order_by(SimulatedTrade.entry_date.desc())
    result = await db.execute(stmt)
    trades = result.scalars().all()
    
    return trades

