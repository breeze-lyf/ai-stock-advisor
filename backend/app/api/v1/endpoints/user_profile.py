"""
用户投资偏好 API
管理用户投资画像、仪表盘配置等
"""
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.onboarding import UserInvestmentProfile, UserDashboardConfig

router = APIRouter()


@router.get("/profile")
async def get_investment_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的投资画像"""
    stmt = select(UserInvestmentProfile).where(UserInvestmentProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        return {
            "status": "success",
            "profile": None,
        }

    return {
        "status": "success",
        "profile": {
            "risk_tolerance": profile.risk_tolerance,
            "risk_tolerance_score": profile.risk_tolerance_score,
            "investment_experience": profile.investment_experience,
            "investment_years": profile.investment_years,
            "preferred_markets": profile.preferred_markets.split(",") if profile.preferred_markets else [],
            "default_market": profile.default_market,
            "investment_style": profile.investment_style,
            "investment_horizon": profile.investment_horizon,
            "portfolio_size": profile.portfolio_size,
            "target_annual_return": float(profile.target_annual_return) if profile.target_annual_return else None,
            "onboarding_completed": profile.onboarding_completed,
            "onboarding_completed_at": profile.onboarding_completed_at.isoformat() if profile.onboarding_completed_at else None,
        },
    }


@router.post("/profile")
async def create_or_update_profile(
    risk_tolerance: str = Query(..., description="风险偏好 (CONSERVATIVE/MODERATE/AGGRESSIVE)"),
    risk_tolerance_score: int = Query(..., ge=1, le=10, description="风险承受能力评分 (1-10)"),
    investment_experience: str = Query(..., description="投资经验 (BEGINNER/INTERMEDIATE/ADVANCED)"),
    investment_years: Optional[int] = Query(None, ge=0, description="投资年限"),
    preferred_markets: str = Query(..., description="关注市场，逗号分隔 (US,HK,CN)"),
    default_market: str = Query("US", description="默认市场 (US/HK/CN)"),
    investment_style: Optional[str] = Query(None, description="投资风格 (VALUE/GROWTH/MOMENTUM/INCOME)"),
    investment_horizon: Optional[str] = Query(None, description="投资期限 (SHORT/MEDIUM/LONG)"),
    portfolio_size: Optional[str] = Query(None, description="持仓规模 (SMALL/MEDIUM/LARGE)"),
    target_annual_return: Optional[float] = Query(None, ge=0, le=100, description="目标年化收益率"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建或更新用户投资画像"""
    stmt = select(UserInvestmentProfile).where(UserInvestmentProfile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if profile:
        # 更新现有记录
        profile.risk_tolerance = risk_tolerance
        profile.risk_tolerance_score = risk_tolerance_score
        profile.investment_experience = investment_experience
        profile.investment_years = investment_years
        profile.preferred_markets = preferred_markets
        profile.default_market = default_market
        profile.investment_style = investment_style
        profile.investment_horizon = investment_horizon
        profile.portfolio_size = portfolio_size
        profile.target_annual_return = target_annual_return
        profile.onboarding_completed = True
        profile.onboarding_completed_at = datetime.utcnow()
    else:
        # 创建新记录
        profile = UserInvestmentProfile(
            user_id=current_user.id,
            risk_tolerance=risk_tolerance,
            risk_tolerance_score=risk_tolerance_score,
            investment_experience=investment_experience,
            investment_years=investment_years,
            preferred_markets=preferred_markets,
            default_market=default_market,
            investment_style=investment_style,
            investment_horizon=investment_horizon,
            portfolio_size=portfolio_size,
            target_annual_return=target_annual_return,
            onboarding_completed=True,
            onboarding_completed_at=datetime.utcnow(),
        )
        db.add(profile)

    await db.commit()
    await db.refresh(profile)

    return {
        "status": "success",
        "profile": {
            "risk_tolerance": profile.risk_tolerance,
            "risk_tolerance_score": profile.risk_tolerance_score,
            "investment_experience": profile.investment_experience,
            "investment_years": profile.investment_years,
            "preferred_markets": profile.preferred_markets.split(",") if profile.preferred_markets else [],
            "default_market": profile.default_market,
            "investment_style": profile.investment_style,
            "investment_horizon": profile.investment_horizon,
            "portfolio_size": profile.portfolio_size,
            "target_annual_return": float(profile.target_annual_return) if profile.target_annual_return else None,
            "onboarding_completed": profile.onboarding_completed,
        },
    }


@router.get("/dashboard-config")
async def get_dashboard_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的仪表盘配置"""
    stmt = select(UserDashboardConfig).where(UserDashboardConfig.user_id == current_user.id)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        # 返回默认配置
        return {
            "status": "success",
            "config": {
                "theme": "light",
                "layout_config": {},
                "show_portfolio_summary": True,
                "show_market_overview": True,
                "show_ai_signals": True,
                "show_news_feed": True,
                "show_watchlist": True,
                "default_view": "dashboard",
            },
        }

    return {
        "status": "success",
        "config": {
            "theme": config.theme,
            "color_scheme": config.color_scheme,
            "layout_config": config.layout_config,
            "show_portfolio_summary": config.show_portfolio_summary,
            "show_market_overview": config.show_market_overview,
            "show_ai_signals": config.show_ai_signals,
            "show_news_feed": config.show_news_feed,
            "show_watchlist": config.show_watchlist,
            "default_view": config.default_view,
        },
    }


@router.post("/dashboard-config")
async def update_dashboard_config(
    theme: Optional[str] = Query(None, description="主题 (light/dark/auto)"),
    color_scheme: Optional[str] = Query(None, description="配色方案 (blue/green/purple)"),
    show_portfolio_summary: Optional[bool] = Query(None),
    show_market_overview: Optional[bool] = Query(None),
    show_ai_signals: Optional[bool] = Query(None),
    show_news_feed: Optional[bool] = Query(None),
    show_watchlist: Optional[bool] = Query(None),
    default_view: Optional[str] = Query(None, description="默认视图"),
    layout_config: Optional[Dict[str, Any]] = Body(None, description="布局配置 (JSON)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新用户仪表盘配置"""
    stmt = select(UserDashboardConfig).where(UserDashboardConfig.user_id == current_user.id)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        # 创建新配置
        config = UserDashboardConfig(
            user_id=current_user.id,
            theme=theme or "light",
            color_scheme=color_scheme,
            layout_config=layout_config or {},
            show_portfolio_summary=show_portfolio_summary if show_portfolio_summary is not None else True,
            show_market_overview=show_market_overview if show_market_overview is not None else True,
            show_ai_signals=show_ai_signals if show_ai_signals is not None else True,
            show_news_feed=show_news_feed if show_news_feed is not None else True,
            show_watchlist=show_watchlist if show_watchlist is not None else True,
            default_view=default_view or "dashboard",
        )
        db.add(config)
    else:
        # 更新现有配置
        if theme is not None:
            config.theme = theme
        if color_scheme is not None:
            config.color_scheme = color_scheme
        if layout_config is not None:
            config.layout_config = layout_config
        if show_portfolio_summary is not None:
            config.show_portfolio_summary = show_portfolio_summary
        if show_market_overview is not None:
            config.show_market_overview = show_market_overview
        if show_ai_signals is not None:
            config.show_ai_signals = show_ai_signals
        if show_news_feed is not None:
            config.show_news_feed = show_news_feed
        if show_watchlist is not None:
            config.show_watchlist = show_watchlist
        if default_view is not None:
            config.default_view = default_view

    await db.commit()
    await db.refresh(config)

    return {
        "status": "success",
        "config": {
            "theme": config.theme,
            "color_scheme": config.color_scheme,
            "layout_config": config.layout_config,
            "show_portfolio_summary": config.show_portfolio_summary,
            "show_market_overview": config.show_market_overview,
            "show_ai_signals": config.show_ai_signals,
            "show_news_feed": config.show_news_feed,
            "show_watchlist": config.show_watchlist,
            "default_view": config.default_view,
        },
    }
