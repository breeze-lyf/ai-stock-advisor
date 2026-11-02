"""Advice records (复盘/战绩): capture actionable recommendations and evaluate them after the horizon."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Optional

from sqlalchemy import select

from app.models.agent_p2 import AgentAdviceRecord

logger = logging.getLogger(__name__)

DEFAULT_HORIZON_DAYS = 20
HOLD_TOLERANCE_PCT = 5.0  # HOLD counts as hit if the price did not fall more than this
_TAG_RE = re.compile(r"【建议】\s*([A-Za-z0-9.\-]{1,15})\s*[|｜]\s*(BUY|SELL|HOLD)\s*[|｜]\s*(\d{1,3})\s*[|｜]?\s*(.*)", re.I)


def parse_direction(text: Optional[str]) -> Optional[str]:
    t = (text or "").upper()
    if not t:
        return None
    if any(k in t for k in ("卖出", "清仓", "减仓", "止盈", "SELL", "回避")):
        return "SELL"
    if any(k in t for k in ("买入", "加仓", "建仓", "增持", "BUY", "低吸")):
        return "BUY"
    if any(k in t for k in ("持有", "观望", "HOLD", "等待")):
        return "HOLD"
    return None


def parse_horizon_days(text: Optional[str]) -> int:
    t = text or ""
    if "日内" in t:
        return 1
    if "0-5" in t or "5天" in t:
        return 5
    if "1-2周" in t or "周" in t:
        return 10
    if "1-3月" in t:
        return 60
    if "3月以上" in t or "长线" in t:
        return 90
    return DEFAULT_HORIZON_DAYS


def parse_answer_tags(answer: str) -> list[dict]:
    out = []
    for m in _TAG_RE.finditer(answer or ""):
        out.append({"ticker": m.group(1).upper(), "direction": m.group(2).upper(),
                    "horizon_days": max(1, min(int(m.group(3)), 365)), "rationale": m.group(4).strip()[:500]})
    return out


def strip_answer_tags(answer: str) -> str:
    return _TAG_RE.sub("", answer or "").rstrip()


def _f(v) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def from_diagnosis(d: dict) -> Optional[dict]:
    direction = parse_direction(d.get("immediate_action")) or parse_direction(d.get("summary_status"))
    if not direction or not d.get("ticker"):
        return None
    return {
        "ticker": str(d["ticker"]).upper(), "direction": direction,
        "horizon_days": parse_horizon_days(d.get("investment_horizon")),
        "price_at": _f(d.get("current_price")), "target_price": _f(d.get("target_price")),
        "stop_loss": _f(d.get("stop_loss_price")),
        "rationale": (d.get("core_logic_summary") or d.get("action_advice") or d.get("immediate_action") or "")[:500],
    }


async def record_advice(db, user_id: str, items: list[dict], source: str, conversation_id: Optional[str] = None,
                        price_fn: Optional[Callable[[str], Awaitable[Optional[float]]]] = None) -> list[AgentAdviceRecord]:
    """Persist advice; dedupe same user+ticker+direction within 24h."""
    rows = []
    now = datetime.utcnow()
    for it in items:
        dup = (await db.execute(select(AgentAdviceRecord.id).where(
            AgentAdviceRecord.user_id == user_id, AgentAdviceRecord.ticker == it["ticker"],
            AgentAdviceRecord.direction == it["direction"], AgentAdviceRecord.created_at > now - timedelta(hours=24),
        ))).first()
        if dup:
            continue
        price = it.get("price_at")
        if price is None and price_fn is not None:
            try:
                price = await price_fn(it["ticker"])
            except Exception as e:
                logger.info(f"advice price lookup failed {it['ticker']}: {e}")
        horizon = int(it.get("horizon_days") or DEFAULT_HORIZON_DAYS)
        row = AgentAdviceRecord(
            user_id=user_id, ticker=it["ticker"], direction=it["direction"], price_at=price, horizon_days=horizon,
            target_price=it.get("target_price"), stop_loss=it.get("stop_loss"), rationale=it.get("rationale"),
            source=source, conversation_id=conversation_id, due_at=now + timedelta(days=horizon), created_at=now,
        )
        db.add(row)
        rows.append(row)
    if rows:
        await db.commit()
    return rows


def judge(direction: str, price_at: float, eval_price: float) -> tuple[float, bool]:
    ret = (eval_price - price_at) / price_at * 100.0
    if direction == "BUY":
        return ret, ret > 0
    if direction == "SELL":
        return ret, ret < 0
    return ret, ret > -HOLD_TOLERANCE_PCT


async def evaluate_due(db, price_fn: Callable[[str], Awaitable[Optional[float]]], now: Optional[datetime] = None,
                       limit: int = 200) -> int:
    now = now or datetime.utcnow()
    rows = (await db.execute(select(AgentAdviceRecord).where(
        AgentAdviceRecord.status == "open", AgentAdviceRecord.due_at <= now).limit(limit))).scalars().all()
    done = 0
    cache: dict[str, Optional[float]] = {}
    for r in rows:
        if r.ticker not in cache:
            try:
                cache[r.ticker] = await price_fn(r.ticker)
            except Exception as e:
                logger.info(f"advice eval price failed {r.ticker}: {e}")
                cache[r.ticker] = None
        price = cache[r.ticker]
        if not price or not r.price_at:
            if not r.price_at or (now - r.due_at) > timedelta(days=7):
                r.status = "error"  # cannot be judged
            continue
        r.eval_price = price
        r.return_pct, r.hit = judge(r.direction, r.price_at, price)
        r.status, r.evaluated_at = "evaluated", now
        done += 1
    await db.commit()
    return done


async def stats(db, user_id: str) -> dict:
    rows = (await db.execute(select(AgentAdviceRecord).where(AgentAdviceRecord.user_id == user_id))).scalars().all()
    ev = [r for r in rows if r.status == "evaluated"]
    hits = [r for r in ev if r.hit]
    by_dir = {}
    for d in ("BUY", "SELL", "HOLD"):
        e = [r for r in ev if r.direction == d]
        by_dir[d] = {"evaluated": len(e), "hits": sum(1 for r in e if r.hit)}
    avg = sum((r.return_pct or 0) * (1 if r.direction != "SELL" else -1) for r in ev) / len(ev) if ev else None
    return {"total": len(rows), "open": sum(1 for r in rows if r.status == "open"), "evaluated": len(ev),
            "hits": len(hits), "hit_rate": (len(hits) / len(ev)) if ev else None,
            "avg_directional_return_pct": avg, "by_direction": by_dir}


async def system_price(db, ticker: str) -> Optional[float]:
    from app.services.domain.market.market_data import MarketDataService

    cache = await MarketDataService.get_real_time_data(ticker, db, preferred_source="AUTO", price_only=True, skip_news=True)
    return _f(getattr(cache, "current_price", None)) if cache is not None else None
