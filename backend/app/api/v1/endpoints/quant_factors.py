"""
量化因子 API 端点
提供因子管理、分析、回测等功能
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from app.core.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.models.quant_factor import (
    QuantFactor, QuantFactorValue, QuantStrategy,
    QuantSignal, QuantBacktestResult, FactorICHistory,
    QuantOptimizationConfig
)
from app.services.factor_engine import factor_engine
from app.services.factor_research import factor_research_service
from app.services.portfolio_optimizer import portfolio_optimizer
from app.services.quant_backtest import quant_backtest_engine, BacktestConfig
from app.services.quant_signal import signal_generator, risk_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 因子管理 ====================

@router.get("/factors")
async def list_factors(
    category: Optional[str] = Query(None, description="因子类别"),
    is_active: bool = Query(True, description="是否活跃"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取因子列表"""
    conditions = [QuantFactor.is_active == is_active]
    if category:
        conditions.append(QuantFactor.category == category)

    stmt = select(QuantFactor).where(and_(*conditions)).order_by(QuantFactor.name)
    result = await db.execute(stmt)
    factors = result.scalars().all()

    return {
        "factors": [
            {
                "id": f.id,
                "name": f.name,
                "code_name": f.code_name,
                "category": f.category,
                "description": f.description,
                "formula": f.formula,
                "ic_mean": float(f.ic_mean) if f.ic_mean else None,
                "ic_ir": float(f.ic_ir) if f.ic_ir else None,
                "rank_ic_mean": float(f.rank_ic_mean) if f.rank_ic_mean else None,
                "rank_ic_ir": float(f.rank_ic_ir) if f.rank_ic_ir else None,
                "is_public": f.is_public,
                "is_custom": f.is_custom,
            }
            for f in factors
        ],
        "total": len(factors),
    }


@router.get("/factors/{factor_id}")
async def get_factor(
    factor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取因子详情"""
    stmt = select(QuantFactor).where(QuantFactor.id == factor_id)
    result = await db.execute(stmt)
    factor = result.scalar()

    if not factor:
        raise HTTPException(status_code=404, detail="Factor not found")

    return {
        "id": factor.id,
        "name": factor.name,
        "code_name": factor.code_name,
        "category": factor.category,
        "description": factor.description,
        "formula": factor.formula,
        "calculation_params": factor.calculation_params,
        "lookback_period": factor.lookback_period,
        "decay_period": factor.decay_period,
        "data_source": factor.data_source,
        "frequency": factor.frequency,
        "performance": {
            "ic_mean": float(factor.ic_mean) if factor.ic_mean else None,
            "ic_ir": float(factor.ic_ir) if factor.ic_ir else None,
            "rank_ic_mean": float(factor.rank_ic_mean) if factor.rank_ic_mean else None,
            "rank_ic_ir": float(factor.rank_ic_ir) if factor.rank_ic_ir else None,
            "annual_return": float(factor.annual_return) if factor.annual_return else None,
            "sharpe_ratio": float(factor.sharpe_ratio) if factor.sharpe_ratio else None,
            "max_drawdown": float(factor.max_drawdown) if factor.max_drawdown else None,
            "win_rate": float(factor.win_rate) if factor.win_rate else None,
            "turnover_rate": float(factor.turnover_rate) if factor.turnover_rate else None,
        },
    }


@router.post("/factors")
async def create_factor(
    factor_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建自定义因子"""
    factor = QuantFactor(
        name=factor_data["name"],
        code_name=factor_data["code_name"],
        category=factor_data.get("category", "CUSTOM"),
        description=factor_data.get("description"),
        formula=factor_data.get("formula"),
        calculation_params=factor_data.get("calculation_params"),
        lookback_period=factor_data.get("lookback_period", 252),
        decay_period=factor_data.get("decay_period", 0),
        data_source=factor_data.get("data_source", "market_data"),
        frequency=factor_data.get("frequency", "DAILY"),
        is_public=factor_data.get("is_public", False),
        is_custom=True,
        created_by=current_user.username,
    )

    db.add(factor)
    await db.commit()
    await db.refresh(factor)

    return {"id": factor.id, "message": "Factor created successfully"}


@router.delete("/factors/{factor_id}")
async def delete_factor(
    factor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除因子"""
    stmt = select(QuantFactor).where(QuantFactor.id == factor_id)
    result = await db.execute(stmt)
    factor = result.scalar()

    if not factor:
        raise HTTPException(status_code=404, detail="Factor not found")

    # 只能删除自定义因子
    if not factor.is_custom:
        raise HTTPException(status_code=403, detail="Cannot delete preset factors")

    await db.delete(factor)
    await db.commit()

    return {"message": "Factor deleted successfully"}


# ==================== 因子分析 ====================

@router.get("/factors/{factor_id}/ic-analysis")
async def factor_ic_analysis(
    factor_id: str,
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    forward_period: int = Query(5, description="前瞻期数"),
    method: str = Query("rank", description="IC 计算方法：rank/normal"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """因子 IC 分析"""
    result = await factor_research_service.calculate_ic(
        db, factor_id, start_date, end_date, forward_period, method
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/factors/{factor_id}/layered-backtest")
async def factor_layered_backtest(
    factor_id: str,
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    n_layers: int = Query(10, description="分层数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """因子分层回测"""
    result = await factor_research_service.calculate_layered_backtest(
        db, factor_id, start_date, end_date, n_layers
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/factors/{factor_id}/turnover")
async def factor_turnover_analysis(
    factor_id: str,
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """因子换手率分析"""
    result = await factor_research_service.calculate_factor_turnover(
        db, factor_id, start_date, end_date
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/factors/{factor_id}/decay")
async def factor_decay_analysis(
    factor_id: str,
    start_date: date = Query(..., description="开始日期"),
    end_date: date = Query(..., description="结束日期"),
    max_lag: int = Query(20, description="最大滞后期"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """因子衰减分析"""
    result = await factor_research_service.analyze_factor_decay(
        db, factor_id, start_date, end_date, max_lag
    )

    return result


# ==================== 组合优化 ====================

@router.post("/optimize")
async def optimize_portfolio(
    optimizer_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    组合优化

    optimizer_type: "mean_variance" / "black_litterman" / "risk_parity" / "hrp" / "min_volatility" / "max_sharpe"
    """
    optimizer_type = optimizer_data.get("optimizer_type", "mean_variance")

    # 获取预期收益率和协方差矩阵
    # 实际应从数据库或外部服务获取
    # 这里简化处理

    if optimizer_type == "mean_variance":
        result = portfolio_optimizer.mean_variance_optimization(
            expected_returns=optimizer_data.get("expected_returns"),
            cov_matrix=optimizer_data.get("cov_matrix"),
            target_return=optimizer_data.get("target_return"),
            target_volatility=optimizer_data.get("target_volatility"),
            min_weight=optimizer_data.get("min_weight", 0.0),
            max_weight=optimizer_data.get("max_weight", 1.0),
            sector_constraints=optimizer_data.get("sector_constraints"),
        )
    elif optimizer_type == "black_litterman":
        result = portfolio_optimizer.black_litterman(
            market_cap=optimizer_data.get("market_cap"),
            cov_matrix=optimizer_data.get("cov_matrix"),
            views=optimizer_data.get("views", []),
            tau=optimizer_data.get("tau", 0.05),
            risk_aversion=optimizer_data.get("risk_aversion", 2.5),
        )
    elif optimizer_type == "risk_parity":
        result = portfolio_optimizer.risk_parity(
            cov_matrix=optimizer_data.get("cov_matrix"),
            expected_returns=optimizer_data.get("expected_returns"),
        )
    elif optimizer_type == "hrp":
        result = portfolio_optimizer.hierarchical_risk_parity(
            returns=optimizer_data.get("returns"),
            cov_matrix=optimizer_data.get("cov_matrix"),
        )
    elif optimizer_type == "min_volatility":
        result = portfolio_optimizer.minimum_volatility(
            cov_matrix=optimizer_data.get("cov_matrix"),
        )
    elif optimizer_type == "max_sharpe":
        result = portfolio_optimizer.maximum_sharpe(
            expected_returns=optimizer_data.get("expected_returns"),
            cov_matrix=optimizer_data.get("cov_matrix"),
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown optimizer type: {optimizer_type}")

    return result


# ==================== 量化回测 ====================

@router.post("/backtest/run")
async def run_backtest(
    backtest_config: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    执行量化回测

    backtest_config:
        - start_date: 开始日期
        - end_date: 结束日期
        - factor_ids: 因子 ID 列表
        - initial_capital: 初始资金
        - commission_rate: 手续费率
        - max_position_pct: 单个股最大仓位
        - rebalance_frequency: 调仓频率
    """
    config = BacktestConfig(
        name=backtest_config.get("name", "Backtest"),
        start_date=backtest_config["start_date"],
        end_date=backtest_config["end_date"],
        initial_capital=backtest_config.get("initial_capital", 1000000),
        commission_rate=backtest_config.get("commission_rate", 0.0003),
        max_position_pct=backtest_config.get("max_position_pct", 10.0),
        rebalance_frequency=backtest_config.get("rebalance_frequency", "WEEKLY"),
    )

    factor_ids = backtest_config.get("factor_ids", [])

    result = await quant_backtest_engine.run_backtest(
        db, config, factor_ids=factor_ids
    )

    return {
        "total_return": result.total_return,
        "annual_return": result.annual_return,
        "sharpe_ratio": result.sharpe_ratio,
        "max_drawdown": result.max_drawdown,
        "volatility": result.volatility,
        "total_trades": result.total_trades,
        "win_rate": result.win_rate,
        "equity_curve": result.equity_curve,
        "monthly_returns": result.monthly_returns,
    }


# ==================== 策略管理 ====================

@router.get("/strategies")
async def list_strategies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取策略列表"""
    stmt = select(QuantStrategy).where(QuantStrategy.user_id == current_user.id)
    result = await db.execute(stmt)
    strategies = result.scalars().all()

    return {
        "strategies": [
            {
                "id": s.id,
                "name": s.name,
                "strategy_type": s.strategy_type,
                "factor_weights": s.factor_weights,
                "rebalance_frequency": s.rebalance_frequency,
                "is_active": s.is_active,
            }
            for s in strategies
        ],
        "total": len(strategies),
    }


@router.post("/strategies")
async def create_strategy(
    strategy_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建策略"""
    strategy = QuantStrategy(
        user_id=current_user.id,
        name=strategy_data["name"],
        description=strategy_data.get("description"),
        strategy_type=strategy_data["strategy_type"],
        factor_weights=strategy_data.get("factor_weights", {}),
        rebalance_frequency=strategy_data.get("rebalance_frequency", "WEEKLY"),
        max_position_pct=strategy_data.get("max_position_pct", 10.0),
        max_stocks=strategy_data.get("max_stocks", 50),
        stop_loss_pct=strategy_data.get("stop_loss_pct", 10.0),
    )

    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)

    return {"id": strategy.id, "message": "Strategy created successfully"}


@router.post("/strategies/{strategy_id}/generate-signals")
async def generate_strategy_signals(
    strategy_id: str,
    trade_date: Optional[date] = Query(None, description="交易日期，默认今天"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成策略信号"""
    stmt = select(QuantStrategy).where(
        and_(
            QuantStrategy.id == strategy_id,
            QuantStrategy.user_id == current_user.id,
        )
    )
    result = await db.execute(stmt)
    strategy = result.scalar()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if trade_date is None:
        trade_date = date.today()

    signals = await signal_generator.generate_signals(db, trade_date, strategy)
    await signal_generator.save_signals(db, signals)

    return {
        "message": f"Generated {len(signals)} signals",
        "signals": [
            {
                "ticker": s.ticker,
                "signal_strength": s.signal_strength,
                "target_weight": s.target_weight,
            }
            for s in signals
        ],
    }


# ==================== 风险管理 ====================

@router.post("/risk/check")
async def check_risk(
    positions_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    风险检查

    positions_data:
        - positions: {ticker: {quantity, price, sector}}
        - portfolio_value: 组合总价值
    """
    positions = positions_data.get("positions", {})
    portfolio_value = positions_data.get("portfolio_value", 0)

    result = risk_manager.check_position_limits(positions, portfolio_value)

    return result


@router.get("/risk/report")
async def get_risk_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取风险报告（需要持仓数据）"""
    # 实际实现需要获取用户持仓和收益率数据
    # 这里返回简化版本

    return {
        "risk_level": "LOW",
        "position_analysis": {"violations": [], "current_exposure": {}},
        "risk_metrics": {},
        "recommendations": [],
    }
