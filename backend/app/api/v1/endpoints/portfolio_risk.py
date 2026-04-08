"""
投资组合风险分析 API
提供风险敞口分析、相关性热力图、再平衡建议、业绩归因等功能
"""
from typing import Optional, Dict
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.portfolio_risk import PortfolioRiskService

router = APIRouter()


@router.get("/risk/sector-exposure")
async def get_sector_exposure(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取行业风险敞口分析

    返回行业分布、集中度指标、赫芬达尔指数等
    """
    result = await PortfolioRiskService.analyze_sector_exposure(db, current_user.id)

    return {
        "status": "success",
        "data": result,
    }


@router.get("/risk/market-cap-exposure")
async def get_market_cap_exposure(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取市值风格暴露分析

    返回大盘/中盘/小盘股的权重配置
    """
    result = await PortfolioRiskService.analyze_market_cap_exposure(db, current_user.id)

    return {
        "status": "success",
        "data": result,
    }


@router.get("/risk/correlation")
async def get_correlation_matrix(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取持仓相关性矩阵

    返回股票之间的相关系数，帮助识别过度集中的风险
    """
    result = await PortfolioRiskService.calculate_correlation_matrix(db, current_user.id)

    return {
        "status": "success",
        "data": result,
    }


@router.get("/risk/rebalance")
async def get_rebalance_suggestions(
    target_weights: Optional[str] = Query(None, description="目标权重配置（JSON 格式）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取再平衡建议

    Args:
        target_weights: 目标权重配置，如 '{"Technology": 0.30, "Healthcare": 0.20}'
    """
    target_weights_dict = None
    if target_weights:
        try:
            target_weights_dict = json.loads(target_weights)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format for target_weights")

    result = await PortfolioRiskService.generate_rebalance_suggestions(
        db, current_user.id, target_weights_dict
    )

    return {
        "status": "success",
        "data": result,
    }


@router.get("/risk/performance-attribution")
async def get_performance_attribution(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取业绩归因分析

    将收益归因于个股选择、行业配置、市场时机三个因素
    """
    result = await PortfolioRiskService.analyze_performance_attribution(db, current_user.id)

    return {
        "status": "success",
        "data": result,
    }


@router.get("/risk/full-report")
async def get_full_risk_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取完整的投资风险报告

    包含所有风险分析指标
    """
    sector_exposure = await PortfolioRiskService.analyze_sector_exposure(db, current_user.id)
    market_cap_exposure = await PortfolioRiskService.analyze_market_cap_exposure(db, current_user.id)
    correlation = await PortfolioRiskService.calculate_correlation_matrix(db, current_user.id)
    rebalance = await PortfolioRiskService.generate_rebalance_suggestions(db, current_user.id)
    performance = await PortfolioRiskService.analyze_performance_attribution(db, current_user.id)

    return {
        "status": "success",
        "data": {
            "sector_exposure": sector_exposure,
            "market_cap_exposure": market_cap_exposure,
            "correlation": correlation,
            "rebalance_suggestions": rebalance,
            "performance_attribution": performance,
        },
    }
