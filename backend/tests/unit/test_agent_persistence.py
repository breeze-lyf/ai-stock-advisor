"""Conversation persistence + API token auth against an in-memory SQLite DB."""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "x" * 40)

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.agent import service
from app.models.agent import AgentConversation, AgentMessage, UserApiToken
from app.models.user import User


class FakeLLM:
    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []

    async def chat(self, messages, tools=None):
        self.calls.append(messages)
        return {"content": self.answers.pop(0)}


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        for t in (User.__table__, AgentConversation.__table__, AgentMessage.__table__, UserApiToken.__table__):
            await conn.run_sync(t.create)
    async with AsyncSession(engine, expire_on_commit=False) as s:
        s.add_all([User(id="u1", email="a@x.com", hashed_password="h"), User(id="u2", email="b@x.com", hashed_password="h")])
        await s.commit()
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_chat_persists_and_reuses_history(db):
    u1 = await db.get(User, "u1")
    r1 = await service.chat(db, u1, "第一问", client=FakeLLM(["答1"]))
    llm = FakeLLM(["答2"])
    r2 = await service.chat(db, u1, "第二问", conversation_id=r1["conversation_id"], client=llm)
    assert r2["conversation_id"] == r1["conversation_id"] and r2["answer"] == "答2"
    contents = [m["content"] for m in llm.calls[0]]
    assert "第一问" in contents and "答1" in contents
    hist = await service.load_history(db, r1["conversation_id"])
    assert [h["role"] for h in hist] == ["user", "assistant", "user", "assistant"]


@pytest.mark.asyncio
async def test_other_user_cannot_continue_conversation(db):
    u1, u2 = await db.get(User, "u1"), await db.get(User, "u2")
    r1 = await service.chat(db, u1, "私密", client=FakeLLM(["x"]))
    with pytest.raises(LookupError):
        await service.chat(db, u2, "偷看", conversation_id=r1["conversation_id"], client=FakeLLM(["y"]))


@pytest.mark.asyncio
async def test_api_token_roundtrip_and_revoke(db):
    from datetime import datetime
    u1 = await db.get(User, "u1")
    row, plain = await service.create_api_token(db, u1, "dingtalk")
    assert row.token_hash != plain and plain not in (row.token_prefix + "x")
    assert (await service.get_user_by_api_token(db, plain)).id == "u1"
    assert await service.get_user_by_api_token(db, "asa_wrong") is None
    assert await service.get_user_by_api_token(db, "") is None
    row.revoked_at = datetime.utcnow()
    await db.commit()
    assert await service.get_user_by_api_token(db, plain) is None
