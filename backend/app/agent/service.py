"""Agent orchestration: LLM resolution, conversation persistence, API tokens."""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import select

from app.agent.llm import ChatClient, OpenAIChatClient, resolve_agent_llm
from app.agent.loop import AgentResult, run_agent
from app.agent.tools import ToolContext
from app.core.config import settings
from app.models.agent import AgentConversation, AgentMessage, UserApiToken

TOKEN_PREFIX = "asa_"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


async def create_api_token(db, user, name: str = "MCP") -> tuple[UserApiToken, str]:
    plain = generate_token()
    row = UserApiToken(user_id=user.id, name=(name or "MCP")[:100], token_hash=hash_token(plain), token_prefix=plain[:10])
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row, plain


async def get_user_by_api_token(db, token: str):
    from app.models.user import User

    if not token or not token.startswith(TOKEN_PREFIX):
        return None
    row = (await db.execute(
        select(UserApiToken).where(UserApiToken.token_hash == hash_token(token), UserApiToken.revoked_at.is_(None))
    )).scalar_one_or_none()
    if row is None:
        return None
    user = (await db.execute(select(User).where(User.id == row.user_id))).scalar_one_or_none()
    if user is not None:
        row.last_used_at = datetime.utcnow()
        row.use_count = (row.use_count or 0) + 1
        await db.commit()
    return user


async def _get_or_create_conversation(db, user, conversation_id: Optional[str], first_message: str, channel: str):
    if conversation_id:
        conv = (await db.execute(
            select(AgentConversation).where(AgentConversation.id == conversation_id, AgentConversation.user_id == user.id)
        )).scalar_one_or_none()
        if conv is None:
            raise LookupError("conversation not found")
        return conv
    conv = AgentConversation(user_id=user.id, title=first_message[:60], channel=channel)
    db.add(conv)
    await db.commit()  # commit early so a failed tool rollback cannot drop it
    return conv


async def load_history(db, conversation_id: str, limit: int = 12) -> list[dict]:
    rows = (await db.execute(
        select(AgentMessage).where(AgentMessage.conversation_id == conversation_id)
        .order_by(AgentMessage.created_at.desc()).limit(limit)
    )).scalars().all()
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]


async def chat(db, user, message: str, conversation_id: Optional[str] = None, channel: str = "web",
               client: Optional[ChatClient] = None) -> dict:
    conv = await _get_or_create_conversation(db, user, conversation_id, message, channel)
    history = await load_history(db, conv.id) if conversation_id else []
    started_at = datetime.utcnow()
    model_info = None
    if client is None:
        target = await resolve_agent_llm(user, db)
        if target is None:
            result = AgentResult("尚未配置可用的 AI 模型：请在「设置」中配置你自己的模型 Key，或联系管理员配置系统默认模型。",
                                 mode="error", stopped_reason="llm_error")
        else:
            model_info = target.public()
            client = OpenAIChatClient(target)
    if client is not None:
        ctx = ToolContext(db=db, user=user)
        result = await run_agent(client, ctx, message, history, max_steps=settings.AGENT_MAX_STEPS)

    trace = {"steps": [s.as_dict() for s in result.steps], "sources": result.sources,
             "mode": result.mode, "stopped_reason": result.stopped_reason}
    db.add(AgentMessage(conversation_id=conv.id, role="user", content=message, created_at=started_at))
    db.add(AgentMessage(conversation_id=conv.id, role="assistant", content=result.answer,
                        tool_trace=json.dumps(trace, ensure_ascii=False, default=str),
                        model=(model_info or {}).get("model")))
    conv.updated_at = datetime.utcnow()
    await db.commit()
    return {"conversation_id": conv.id, "model": model_info, **result.as_dict()}
