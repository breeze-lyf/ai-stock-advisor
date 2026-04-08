"""
策略回测 API
提供回测配置、执行、结果查询等功能
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.backtest import BacktestConfig, BacktestResult, SavedStrategy
from app.services.backtest_engine import backtest_engine

router = APIRouter()


@router.get("/backtest/configs")
async def list_backtest_configs(
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的回测配置列表"""
    conditions = [BacktestConfig.user_id == current_user.id]

    if is_active is not None:
        conditions.append(BacktestConfig.is_active == is_active)

    stmt = select(BacktestConfig).where(and_(*conditions)).order_by(BacktestConfig.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    configs = result.scalars().all()

    return {
        "status": "success",
        "count": len(configs),
        "configs": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "strategy_type": c.strategy_type,
                "tickers": c.tickers.split(",") if c.tickers else [],
                "sector": c.sector,
                "market": c.market,
                "start_date": c.start_date.isoformat(),
                "end_date": c.end_date.isoformat(),
                "initial_capital": float(c.initial_capital),
                "is_active": c.is_active,
                "created_at": c.created_at.isoformat(),
            }
            for c in configs
        ],
    }


@router.get("/backtest/configs/{config_id}")
async def get_backtest_config(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个回测配置"""
    stmt = select(BacktestConfig).where(
        and_(
            BacktestConfig.id == config_id,
            BacktestConfig.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    return {
        "status": "success",
        "config": {
            "id": config.id,
            "name": config.name,
            "description": config.description,
            "strategy_type": config.strategy_type,
            "tickers": config.tickers.split(",") if config.tickers else [],
            "sector": config.sector,
            "market": config.market,
            "entry_conditions": config.entry_conditions,
            "exit_conditions": config.exit_conditions,
            "position_size_pct": float(config.position_size_pct),
            "max_positions": config.max_positions,
            "start_date": config.start_date.isoformat(),
            "end_date": config.end_date.isoformat(),
            "initial_capital": float(config.initial_capital),
            "commission_rate": float(config.commission_rate),
            "slippage_pct": float(config.slippage_pct),
            "is_active": config.is_active,
            "is_public": config.is_public,
        },
    }


@router.post("/backtest/configs")
async def create_backtest_config(
    name: str = Query(..., description="配置名称"),
    description: Optional[str] = Query(None, description="描述"),
    strategy_type: str = Query(..., description="策略类型"),
    tickers: Optional[str] = Query(None, description="股票代码列表，逗号分隔"),
    sector: Optional[str] = Query(None, description="行业"),
    market: Optional[str] = Query(None, description="市场 (US/HK/CN)"),
    entry_conditions: Dict[str, Any] = Body(None, description="入场条件 (JSON)"),
    exit_conditions: Dict[str, Any] = Body(None, description="出场条件 (JSON)"),
    position_size_pct: float = Query(20.0, ge=1, le=100, description="仓位百分比"),
    max_positions: int = Query(5, ge=1, le=20, description="最大持仓数"),
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期 (YYYY-MM-DD)"),
    initial_capital: float = Query(1000000, ge=10000, description="初始资金"),
    commission_rate: float = Query(0.0003, ge=0, description="手续费率"),
    slippage_pct: float = Query(0.001, ge=0, description="滑点"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建回测配置"""
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    if start >= end:
        raise HTTPException(status_code=400, detail="Start date must be before end date")

    config = BacktestConfig(
        user_id=current_user.id,
        name=name,
        description=description,
        strategy_type=strategy_type,
        tickers=tickers,
        sector=sector,
        market=market,
        entry_conditions=entry_conditions,
        exit_conditions=exit_conditions,
        position_size_pct=position_size_pct,
        max_positions=max_positions,
        start_date=start,
        end_date=end,
        initial_capital=initial_capital,
        commission_rate=commission_rate,
        slippage_pct=slippage_pct,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)

    return {
        "status": "success",
        "config": {
            "id": config.id,
            "name": config.name,
            "strategy_type": config.strategy_type,
            "created_at": config.created_at.isoformat(),
        },
    }


@router.post("/backtest/configs/{config_id}/run")
async def run_backtest(
    config_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """执行回测"""
    # 获取配置
    stmt = select(BacktestConfig).where(
        and_(
            BacktestConfig.id == config_id,
            BacktestConfig.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    if not config.is_active:
        raise HTTPException(status_code=400, detail="Config is not active")

    # 执行回测
    result = await backtest_engine.run_backtest(db, config)

    return {
        "status": "success",
        "result": {
            "id": result.id,
            "config_id": result.config_id,
            "status": result.status,
            "execution_time_seconds": float(result.execution_time_seconds) if result.execution_time_seconds else None,
            "metrics": {
                "total_return": float(result.total_return) if result.total_return else None,
                "annualized_return": float(result.annualized_return) if result.annualized_return else None,
                "max_drawdown": float(result.max_drawdown) if result.max_drawdown else None,
                "sharpe_ratio": float(result.sharpe_ratio) if result.sharpe_ratio else None,
                "sortino_ratio": float(result.sortino_ratio) if result.sortino_ratio else None,
                "win_rate": float(result.win_rate) if result.win_rate else None,
                "total_trades": result.total_trades,
                "final_capital": float(result.final_capital) if result.final_capital else None,
            },
        },
    }


@router.get("/backtest/results/{result_id}")
async def get_backtest_result(
    result_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取回测结果详情"""
    stmt = select(BacktestResult).where(
        and_(
            BacktestResult.id == result_id,
            BacktestResult.user_id == current_user.id
        )
    )
    result = await db.execute(stmt)
    backtest_result = result.scalar_one_or_none()

    if not backtest_result:
        raise HTTPException(status_code=404, detail="Result not found")

    return {
        "status": "success",
        "result": {
            "id": backtest_result.id,
            "config_id": backtest_result.config_id,
            "status": backtest_result.status,
            "error_message": backtest_result.error_message,
            "execution_time_seconds": float(backtest_result.execution_time_seconds) if backtest_result.execution_time_seconds else None,
            "metrics": {
                "total_return": float(backtest_result.total_return) if backtest_result.total_return else None,
                "annualized_return": float(backtest_result.annualized_return) if backtest_result.annualized_return else None,
                "max_drawdown": float(backtest_result.max_drawdown) if backtest_result.max_drawdown else None,
                "max_drawdown_duration_days": backtest_result.max_drawdown_duration_days,
                "volatility": float(backtest_result.volatility) if backtest_result.volatility else None,
                "sharpe_ratio": float(backtest_result.sharpe_ratio) if backtest_result.sharpe_ratio else None,
                "sortino_ratio": float(backtest_result.sortino_ratio) if backtest_result.sortino_ratio else None,
                "calmar_ratio": float(backtest_result.calmar_ratio) if backtest_result.calmar_ratio else None,
                "total_trades": backtest_result.total_trades,
                "winning_trades": backtest_result.winning_trades,
                "losing_trades": backtest_result.losing_trades,
                "win_rate": float(backtest_result.win_rate) if backtest_result.win_rate else None,
                "avg_win_pct": float(backtest_result.avg_win_pct) if backtest_result.avg_win_pct else None,
                "avg_loss_pct": float(backtest_result.avg_loss_pct) if backtest_result.avg_loss_pct else None,
                "profit_factor": float(backtest_result.profit_factor) if backtest_result.profit_factor else None,
                "avg_holding_period_days": float(backtest_result.avg_holding_period_days) if backtest_result.avg_holding_period_days else None,
                "final_capital": float(backtest_result.final_capital) if backtest_result.final_capital else None,
                "total_commission": float(backtest_result.total_commission) if backtest_result.total_commission else None,
            },
            "equity_curve": backtest_result.equity_curve,
            "trades": backtest_result.trades,
            "monthly_returns": backtest_result.monthly_returns,
        },
    }


@router.get("/backtest/results")
async def list_backtest_results(
    config_id: Optional[str] = Query(None, description="配置 ID"),
    status: Optional[str] = Query(None, description="状态 (PENDING/RUNNING/COMPLETED/FAILED)"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取回测结果列表"""
    conditions = [BacktestResult.user_id == current_user.id]

    if config_id:
        conditions.append(BacktestResult.config_id == config_id)
    if status:
        conditions.append(BacktestResult.status == status.upper())

    stmt = select(BacktestResult).where(
        and_(*conditions)
    ).order_by(BacktestResult.created_at.desc()).limit(limit)

    result = await db.execute(stmt)
    results = result.scalars().all()

    return {
        "status": "success",
        "count": len(results),
        "results": [
            {
                "id": r.id,
                "config_id": r.config_id,
                "status": r.status,
                "total_return": float(r.total_return) if r.total_return else None,
                "sharpe_ratio": float(r.sharpe_ratio) if r.sharpe_ratio else None,
                "max_drawdown": float(r.max_drawdown) if r.max_drawdown else None,
                "total_trades": r.total_trades,
                "created_at": r.created_at.isoformat(),
            }
            for r in results
        ],
    }


@router.get("/backtest/strategies")
async def list_strategies(
    category: Optional[str] = Query(None, description="策略分类"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取预设策略库"""
    conditions = [SavedStrategy.is_active == True]

    if category:
        conditions.append(SavedStrategy.category == category)

    stmt = select(SavedStrategy).where(and_(*conditions)).order_by(SavedStrategy.name)
    result = await db.execute(stmt)
    strategies = result.scalars().all()

    return {
        "status": "success",
        "count": len(strategies),
        "strategies": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "entry_conditions": s.entry_conditions,
                "exit_conditions": s.exit_conditions,
                "default_position_size": float(s.default_position_size),
                "applicable_markets": s.applicable_markets.split(",") if s.applicable_markets else [],
                "historical_return_1y": float(s.historical_return_1y) if s.historical_return_1y else None,
                "historical_sharpe": float(s.historical_sharpe) if s.historical_sharpe else None,
                "historical_max_drawdown": float(s.historical_max_drawdown) if s.historical_max_drawdown else None,
            }
            for s in strategies
        ],
    }
