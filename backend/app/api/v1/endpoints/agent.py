"""Agent chat API + personal API tokens (for MCP clients)."""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import service
from app.agent.loop import DISCLAIMER
from app.agent.tools import TOOLS
from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.rate_limiter import limiter
from app.models.agent import AgentConversation, AgentMessage, UserApiToken
from app.models.user import User

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = None


class TokenCreate(BaseModel):
    name: str = Field("MCP", max_length=100)


@router.post("/chat")
@limiter.limit("20/minute")
async def agent_chat(request: Request, body: ChatRequest, db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    try:
        result = await service.chat(db, current_user, body.message.strip(), body.conversation_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    result["disclaimer"] = DISCLAIMER
    return result


@router.get("/tools")
async def list_tools(current_user: User = Depends(get_current_user)):
    return [{"name": t.name, "title": t.title, "description": t.description} for t in TOOLS]


@router.get("/conversations")
async def list_conversations(limit: int = 30, db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    rows = (await db.execute(
        select(AgentConversation).where(AgentConversation.user_id == current_user.id)
        .order_by(AgentConversation.updated_at.desc()).limit(min(limit, 100))
    )).scalars().all()
    return [{"id": r.id, "title": r.title, "channel": r.channel, "updated_at": r.updated_at} for r in rows]


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    conv = (await db.execute(select(AgentConversation).where(
        AgentConversation.id == conversation_id, AgentConversation.user_id == current_user.id))).scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = (await db.execute(select(AgentMessage).where(AgentMessage.conversation_id == conv.id)
                             .order_by(AgentMessage.created_at.asc()))).scalars().all()
    return {
        "id": conv.id, "title": conv.title,
        "messages": [{"role": m.role, "content": m.content, "created_at": m.created_at,
                      "trace": json.loads(m.tool_trace) if m.tool_trace else None} for m in msgs],
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, db: AsyncSession = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    conv = (await db.execute(select(AgentConversation).where(
        AgentConversation.id == conversation_id, AgentConversation.user_id == current_user.id))).scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conv)
    await db.commit()
    return {"ok": True}


@router.post("/tokens")
async def create_token(body: TokenCreate, db: AsyncSession = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    active = (await db.execute(select(UserApiToken).where(
        UserApiToken.user_id == current_user.id, UserApiToken.revoked_at.is_(None)))).scalars().all()
    if len(active) >= 10:
        raise HTTPException(status_code=400, detail="最多 10 个有效 Token，请先吊销旧 Token")
    row, plain = await service.create_api_token(db, current_user, body.name)
    return {"id": row.id, "name": row.name, "token": plain, "prefix": row.token_prefix,
            "note": "Token 只显示这一次，请妥善保存；用于 MCP: Authorization: Bearer <token>"}


@router.get("/tokens")
async def list_tokens(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (await db.execute(select(UserApiToken).where(UserApiToken.user_id == current_user.id)
                             .order_by(UserApiToken.created_at.desc()))).scalars().all()
    return [{"id": r.id, "name": r.name, "prefix": r.token_prefix, "created_at": r.created_at,
             "last_used_at": r.last_used_at, "revoked": r.revoked_at is not None} for r in rows]


@router.delete("/tokens/{token_id}")
async def revoke_token(token_id: str, db: AsyncSession = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    row = (await db.execute(select(UserApiToken).where(
        UserApiToken.id == token_id, UserApiToken.user_id == current_user.id))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Token not found")
    row.revoked_at = row.revoked_at or datetime.utcnow()
    await db.commit()
    return {"ok": True}
