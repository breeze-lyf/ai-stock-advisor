"""Proactive daily brief (今日简报): per user, the agent reviews holdings + watchlist and writes a short brief."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

import pytz
from sqlalchemy import select

from app.agent.advice import parse_answer_tags, record_advice, strip_answer_tags, system_price
from app.agent.llm import ChatClient, OpenAIChatClient, resolve_agent_llm
from app.agent.loop import run_agent
from app.agent.profile import build_user_memory, load_tickers
from app.agent.tools import ToolContext
from app.core.config import settings
from app.models.agent_p2 import AgentDailyBrief, AgentNotifierConfig

logger = logging.getLogger(__name__)
CN_TZ = pytz.timezone("Asia/Shanghai")
# Brief never runs the slow diagnosis; it only reads data.
BRIEF_TOOLS = {"get_quote", "get_kline_and_technicals", "get_fundamentals", "search_news", "get_portfolio", "macro_snapshot"}


def today_cn(now: Optional[datetime] = None) -> str:
    now = now or datetime.now(pytz.utc)
    if now.tzinfo is None:
        now = pytz.utc.localize(now)
    return now.astimezone(CN_TZ).strftime("%Y-%m-%d")


def brief_prompt(holds: list[str], watch: list[str], date: str) -> str:
    return (
        f"请为我生成 {date} 的「今日简报」。我的持仓：{'、'.join(holds) or '无'}；自选：{'、'.join(watch) or '无'}。\n"
        "要求：先调用 get_portfolio 和必要的 get_quote / search_news / macro_snapshot 获取真实数据（每只最多查一次，最多 8 只重点标的）。\n"
        "输出 Markdown，结构固定为：\n"
        "### 一句话总览\n### 持仓变化（涨跌、盈亏、异动）\n### 风险提示（集中度、事件、技术破位）\n### 今日关注（价位、事件、待办）\n"
        "每部分 2-5 条要点，具体到代码和数字，总长度不超过 600 字。"
    )


async def generate_brief(db, user, client: Optional[ChatClient] = None, force: bool = False,
                         now: Optional[datetime] = None) -> Optional[AgentDailyBrief]:
    date = today_cn(now)
    existing = (await db.execute(select(AgentDailyBrief).where(
        AgentDailyBrief.user_id == user.id, AgentDailyBrief.brief_date == date))).scalar_one_or_none()
    if existing is not None and not force and existing.status == "ok":
        return existing
    holds, watch = await load_tickers(db, user.id)
    if not holds and not watch:
        return None
    model = None
    if client is None:
        target = await resolve_agent_llm(user, db)
        if target is None:
            return None
        model = target.model
        client = OpenAIChatClient(target)
    ctx = ToolContext(db=db, user=user, allowed_tools=BRIEF_TOOLS)
    memory = await build_user_memory(db, user)
    result = await run_agent(client, ctx, brief_prompt(holds, watch, date), [], max_steps=settings.AGENT_MAX_STEPS,
                             extra_system=memory or None)
    tags = parse_answer_tags(result.answer)
    content = strip_answer_tags(result.answer)
    row = existing or AgentDailyBrief(user_id=user.id, brief_date=date)
    row.title = f"{date} 今日简报"
    row.content = content
    row.tickers = json.dumps(holds + watch, ensure_ascii=False)
    row.status = "error" if result.mode == "error" else "ok"
    row.model = model
    row.created_at = datetime.utcnow()
    if existing is None:
        db.add(row)
    await db.commit()
    if tags and row.status == "ok":
        try:
            await record_advice(db, user.id, tags, source="brief", price_fn=lambda t: system_price(db, t))
        except Exception as e:
            logger.warning(f"brief advice record failed: {e}")
            await db.rollback()
    return row


async def push_brief(db, brief: AgentDailyBrief, send_fn=None) -> list[str]:
    from app.agent import notifier
    from app.core.security import decrypt_api_key

    send_fn = send_fn or notifier.send
    configs = (await db.execute(select(AgentNotifierConfig).where(
        AgentNotifierConfig.user_id == brief.user_id, AgentNotifierConfig.enabled.is_(True),
        AgentNotifierConfig.brief_enabled.is_(True)))).scalars().all()
    pushed = []
    for c in configs:
        ok, msg = await send_fn(c.kind, decrypt_api_key(c.url), decrypt_api_key(c.secret) if c.secret else None,
                                brief.title, brief.content + "\n\n> 仅供研究参考，不构成投资建议。")
        c.last_status = (f"{datetime.utcnow():%Y-%m-%d %H:%M}Z " + ("ok" if ok else msg))[:200]
        if ok:
            pushed.append(c.kind)
    brief.pushed_channels = ",".join(pushed) or None
    await db.commit()
    return pushed


async def run_daily_briefs_job(session_factory, max_users: Optional[int] = None) -> int:
    """Scheduler entry. Users with at least one portfolio/watchlist row; capped by AGENT_BRIEF_MAX_USERS."""
    from app.models.portfolio import Portfolio
    from app.models.user import User

    max_users = max_users or settings.AGENT_BRIEF_MAX_USERS
    async with session_factory() as db:
        user_ids = [r[0] for r in (await db.execute(select(Portfolio.user_id).distinct().limit(max_users))).all()]
    n = 0
    for uid in user_ids:
        async with session_factory() as db:
            try:
                user = await db.get(User, uid)
                if user is None or getattr(user, "is_active", True) is False:
                    continue
                brief = await generate_brief(db, user)
                if brief is not None and brief.status == "ok" and not brief.pushed_channels:
                    await push_brief(db, brief)
                n += 1 if brief is not None else 0
            except Exception as e:
                logger.error(f"[Brief] user {uid} failed: {e}")
                await db.rollback()
    return n


async def run_advice_review_job(session_factory) -> int:
    from app.agent.advice import evaluate_due

    async with session_factory() as db:
        return await evaluate_due(db, lambda t: system_price(db, t))
