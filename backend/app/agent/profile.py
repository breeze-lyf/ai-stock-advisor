"""User memory for the agent: investment profile (reuses onboarding UserInvestmentProfile) + holdings/watchlist."""
from __future__ import annotations

import logging

from sqlalchemy import select

logger = logging.getLogger(__name__)

RISK = {"CONSERVATIVE": "保守", "MODERATE": "稳健", "AGGRESSIVE": "激进"}
HORIZON = {"SHORT": "短线（数天~数周）", "MEDIUM": "中线（1~6 个月）", "LONG": "长线（半年以上）"}
STYLE = {"VALUE": "价值", "GROWTH": "成长", "MOMENTUM": "趋势/动量", "INCOME": "红利/收益", "BALANCED": "均衡"}
MARKETS = {"US": "美股", "HK": "港股", "CN": "A股"}


def format_profile(profile) -> str:
    if profile is None:
        return "用户尚未填写投资画像：回答保持中性稳健，可在合适时提醒 TA 到「设置 → 投资画像」补充。"
    markets = [MARKETS.get(m.strip(), m.strip()) for m in (profile.preferred_markets or "").split(",") if m.strip()]
    parts = [
        f"风险偏好：{RISK.get(profile.risk_tolerance, profile.risk_tolerance or '未填')}（{profile.risk_tolerance_score or '-'}/10）",
        f"投资周期：{HORIZON.get(profile.investment_horizon or '', profile.investment_horizon or '未填')}",
        f"投资风格：{STYLE.get(profile.investment_style or '', profile.investment_style or '未填')}",
        f"关注市场：{'、'.join(markets) or '未填'}",
    ]
    return "用户投资画像（请据此调整建议的仓位、周期与措辞，不要超出其风险承受能力）：" + "；".join(parts)


async def load_tickers(db, user_id: str) -> tuple[list[str], list[str]]:
    """Return (holdings, watchlist) tickers. quantity == 0 means watch-only."""
    from app.models.portfolio import Portfolio

    rows = (await db.execute(select(Portfolio.ticker, Portfolio.quantity).where(Portfolio.user_id == user_id)
                             .order_by(Portfolio.sort_order))).all()
    holds = [t for t, q in rows if (q or 0) > 0]
    watch = [t for t, q in rows if not (q or 0) > 0]
    return holds, watch


async def build_user_memory(db, user) -> str:
    if user is None or db is None:
        return ""
    try:
        from app.models.onboarding import UserInvestmentProfile

        async with db.begin_nested():  # savepoint: a failure must not expire caller's objects
            profile = (await db.execute(select(UserInvestmentProfile).where(UserInvestmentProfile.user_id == user.id))).scalar_one_or_none()
            holds, watch = await load_tickers(db, user.id)
    except Exception as e:  # memory is best-effort, never block chat
        logger.warning(f"agent memory unavailable: {e}")
        return ""
    lines = [format_profile(profile)]
    if holds:
        lines.append("用户持仓：" + "、".join(holds[:30]))
    if watch:
        lines.append("用户自选（未持仓）：" + "、".join(watch[:30]))
    return "\n".join(lines)
