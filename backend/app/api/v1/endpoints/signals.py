"""
AI 信号历史 API
提供信号记录查询、表现统计等功能
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.ai_signal_history import SignalStatus, SignalType
from app.services.signal_tracker import signal_tracker_service

router = APIRouter()


@router.get("/signals")
async def get_signals(
    ticker: Optional[str] = Query(None, description="股票代码"),
    status: Optional[str] = Query(None, description="信号状态 (ACTIVE/CLOSED/EXPIRED)"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取用户的 AI 信号历史记录。

    【业务逻辑】
    - 系统会追踪 AI 生成的每一条具备买入倾向的指令（信号）。
    - 每个信号包含：触发价格、止损/止盈价格点位。
    - 用户可以按股票代码或状态（活跃/已关闭/已过期）筛选。
    """
    status_enum = None
    if status:
        try:
            status_enum = SignalStatus(status.upper())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Valid values: ACTIVE, CLOSED, EXPIRED, CANCELLED"
            )

    signals = await signal_tracker_service.get_user_signals(
        db,
        current_user.id,
        ticker=ticker,
        status=status_enum,
        limit=limit,
    )

    return {
        "status": "success",
        "count": len(signals),
        "signals": signals,
    }


@router.get("/signals/performance")
async def get_performance(
    period: str = Query("MONTHLY", description="统计周期 (DAILY/WEEKLY/MONTHLY/YEARLY/ALL)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取 AI 信号的表现归因统计。

    【量化评价逻辑】
    - 胜率 (Win Rate)：盈利信号数 / 总成交信号数。
    - 盈亏比 (Avg PnL)：所有已平仓信号的平均收益表现。
    - 最佳/最差信号：辅助用户回顾 AI 的极端研判表现。
    """
    valid_periods = ["DAILY", "WEEKLY", "MONTHLY", "YEARLY", "ALL"]
    if period.upper() not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Valid values: {', '.join(valid_periods)}"
        )

    performance = await signal_tracker_service.get_user_performance(
        db,
        current_user.id,
        period=period.upper(),
    )

    return {
        "status": "success",
        "performance": performance,
    }


@router.post("/signals/{signal_id}/close")
async def close_signal(
    signal_id: str,
    exit_price: float = Query(..., description="退出价格"),
    exit_reason: str = Query("MANUAL", description="退出原因 (MANUAL/TARGET_HIT/STOP_LOSS/TIME_EXPIRED)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    手动关闭信号

    当用户实际执行交易时调用，记录退出价格和原因
    """
    valid_reasons = ["MANUAL", "TARGET_HIT", "STOP_LOSS", "TIME_EXPIRED"]
    if exit_reason.upper() not in valid_reasons:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid exit_reason. Valid values: {', '.join(valid_reasons)}"
        )

    signal = await signal_tracker_service.close_signal(
        db,
        signal_id,
        exit_price,
        exit_reason.upper(),
    )

    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    # 验证信号属于当前用户
    if signal.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "status": "success",
        "signal": signal_tracker_service._signal_to_dict(signal),
    }


@router.get("/signals/{signal_id}")
async def get_signal(
    signal_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个信号的详细信息"""
    signals = await signal_tracker_service.get_user_signals(
        db,
        current_user.id,
        limit=1,
    )

    # 查找匹配的信号
    signal = next((s for s in signals if s["id"] == signal_id), None)

    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    # 验证信号属于当前用户
    stmt = select(AISignalHistory).where(AISignalHistory.id == signal_id)
    result = await db.execute(stmt)
    signal_obj = result.scalar_one_or_none()

    if not signal_obj or signal_obj.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Signal not found")

    return {
        "status": "success",
        "signal": signal,
    }


from sqlalchemy.future import select
from app.models.ai_signal_history import AISignalHistory
