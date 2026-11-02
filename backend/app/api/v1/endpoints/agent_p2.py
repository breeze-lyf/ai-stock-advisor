"""Agent P2 API: daily briefs, push channels, advice records (复盘), public trial."""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import advice as advice_svc
from app.agent import brief as brief_svc
from app.agent import notifier, trial
from app.agent.loop import DISCLAIMER
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limiter import limiter
from app.models.agent_p2 import AgentAdviceRecord, AgentDailyBrief, AgentNotifierConfig
from app.models.user import User

router = APIRouter()


def _brief_out(b: AgentDailyBrief) -> dict:
    return {"id": b.id, "date": b.brief_date, "title": b.title, "content": b.content, "status": b.status,
            "tickers": json.loads(b.tickers) if b.tickers else [], "pushed_channels": b.pushed_channels,
            "created_at": b.created_at}


# ------------------------------------------------------------------ briefs
@router.get("/briefs")
async def list_briefs(limit: int = 14, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (await db.execute(select(AgentDailyBrief).where(AgentDailyBrief.user_id == current_user.id)
                             .order_by(AgentDailyBrief.brief_date.desc()).limit(min(limit, 60)))).scalars().all()
    return {"items": [_brief_out(r) for r in rows], "scheduled": settings.AGENT_BRIEF_ENABLED,
            "hour": settings.AGENT_BRIEF_HOUR, "disclaimer": DISCLAIMER}


@router.post("/briefs/generate")
@limiter.limit("3/hour")
async def generate_brief(request: Request, push: bool = False, db: AsyncSession = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    b = await brief_svc.generate_brief(db, current_user, force=True)
    if b is None:
        raise HTTPException(status_code=400, detail="还没有持仓或自选，或未配置可用模型，无法生成简报")
    if push and b.status == "ok":
        await brief_svc.push_brief(db, b)
    return _brief_out(b)


# ------------------------------------------------------------------ notifiers
class NotifierIn(BaseModel):
    kind: str = Field(..., pattern="^(dingtalk|webhook|telegram)$")
    url: str = Field(..., min_length=1, max_length=1000)
    secret: Optional[str] = Field(None, max_length=500)
    enabled: bool = True
    brief_enabled: bool = True


def _mask(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    return v[:28] + "…" if len(v) > 32 else v[:4] + "…"


def _notifier_out(c: AgentNotifierConfig) -> dict:
    from app.core.security import decrypt_api_key

    return {"id": c.id, "kind": c.kind, "url": _mask(decrypt_api_key(c.url)), "has_secret": bool(c.secret),
            "enabled": c.enabled, "brief_enabled": c.brief_enabled, "last_status": c.last_status}


def _enc(v: Optional[str]) -> Optional[str]:
    from app.core.security import encrypt_api_key

    if not v:
        return None
    try:
        return encrypt_api_key(v)
    except ValueError:
        raise HTTPException(status_code=500, detail="服务器未配置 ENCRYPTION_KEY，无法安全保存推送地址")


@router.get("/notifiers")
async def list_notifiers(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (await db.execute(select(AgentNotifierConfig).where(AgentNotifierConfig.user_id == current_user.id))).scalars().all()
    return [_notifier_out(r) for r in rows]


@router.post("/notifiers")
async def create_notifier(body: NotifierIn, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    err = notifier.validate(body.kind, body.url.strip(), body.secret)
    if err:
        raise HTTPException(status_code=400, detail=err)
    count = len((await db.execute(select(AgentNotifierConfig.id).where(AgentNotifierConfig.user_id == current_user.id))).all())
    if count >= 5:
        raise HTTPException(status_code=400, detail="最多配置 5 个推送渠道")
    row = AgentNotifierConfig(user_id=current_user.id, kind=body.kind, url=_enc(body.url.strip()), secret=_enc(body.secret),
                              enabled=body.enabled, brief_enabled=body.brief_enabled)
    db.add(row)
    await db.commit()
    return _notifier_out(row)


async def _own_notifier(db, user, nid) -> AgentNotifierConfig:
    row = (await db.execute(select(AgentNotifierConfig).where(AgentNotifierConfig.id == nid,
                                                              AgentNotifierConfig.user_id == user.id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Notifier not found")
    return row


@router.delete("/notifiers/{nid}")
async def delete_notifier(nid: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await db.delete(await _own_notifier(db, current_user, nid))
    await db.commit()
    return {"ok": True}


@router.post("/notifiers/{nid}/test")
@limiter.limit("10/hour")
async def test_notifier(request: Request, nid: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.core.security import decrypt_api_key

    row = await _own_notifier(db, current_user, nid)
    ok, msg = await notifier.send(row.kind, decrypt_api_key(row.url), decrypt_api_key(row.secret) if row.secret else None,
                                  "今日简报 · 测试消息", "这是一条来自「个人投资智能体」的测试推送。")
    row.last_status = ("测试 ok" if ok else f"测试失败 {msg}")[:200]
    await db.commit()
    return {"ok": ok, "message": msg}


# ------------------------------------------------------------------ advice / 复盘
@router.get("/advice")
async def list_advice(status: Optional[str] = None, limit: int = 100, db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    q = select(AgentAdviceRecord).where(AgentAdviceRecord.user_id == current_user.id)
    if status:
        q = q.where(AgentAdviceRecord.status == status)
    rows = (await db.execute(q.order_by(AgentAdviceRecord.created_at.desc()).limit(min(limit, 500)))).scalars().all()
    keep = ("id", "ticker", "direction", "price_at", "horizon_days", "target_price", "stop_loss", "rationale", "source",
            "conversation_id", "status", "due_at", "eval_price", "return_pct", "hit", "evaluated_at", "created_at")
    return {"items": [{k: getattr(r, k) for k in keep} for r in rows],
            "stats": await advice_svc.stats(db, current_user.id), "disclaimer": DISCLAIMER}


# ------------------------------------------------------------------ public: config + trial
@router.get("/public-config")
async def public_config():
    return {"trial_enabled": settings.AGENT_TRIAL_ENABLED and trial.trial_target() is not None,
            "trial_daily_limit": settings.AGENT_TRIAL_DAILY_LIMIT, "billing_enabled": settings.FEATURE_BILLING_ENABLED,
            "brief_scheduled": settings.AGENT_BRIEF_ENABLED}


class TrialIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


@router.post("/trial/chat")
@limiter.limit("6/minute")
async def trial_chat(request: Request, body: TrialIn, db: AsyncSession = Depends(get_db)):
    if not settings.AGENT_TRIAL_ENABLED:
        raise HTTPException(status_code=404, detail="试用未开启")
    allowed, remaining = await trial.consume_quota(trial.client_ip(request))
    if not allowed:
        raise HTTPException(status_code=429, detail=f"今日免费试用次数已用完（每天 {settings.AGENT_TRIAL_DAILY_LIMIT} 次），注册后可继续使用")
    result = await trial.trial_chat(db, body.message.strip())
    result.update({"remaining": remaining, "disclaimer": DISCLAIMER})
    return result
