"""Agent P2: advice parsing/evaluation, brief generation + push, notifier signing, trial quota/tool scoping, memory."""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "x" * 40)

import base64
import hashlib
import hmac
import json
import urllib.parse
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.agent import advice, brief, notifier, service, trial
from app.agent.tools import ToolContext, execute_tool
from app.models.agent import AgentConversation, AgentMessage, UserApiToken
from app.models.agent_p2 import AgentAdviceRecord, AgentDailyBrief, AgentNotifierConfig
from app.models.onboarding import UserInvestmentProfile
from app.models.portfolio import Portfolio
from app.models.stock import Stock
from app.models.user import User


class FakeLLM:
    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []

    async def chat(self, messages, tools=None):
        self.calls.append({"messages": messages, "tools": tools})
        a = self.answers.pop(0)
        return a if isinstance(a, dict) else {"content": a}


TABLES = (User, Stock, Portfolio, UserInvestmentProfile, AgentConversation, AgentMessage, UserApiToken,
          AgentDailyBrief, AgentNotifierConfig, AgentAdviceRecord)


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        for t in TABLES:
            await conn.run_sync(t.__table__.create)
    async with AsyncSession(engine, expire_on_commit=False) as s:
        s.add(User(id="u1", email="a@x.com", hashed_password="h"))
        s.add_all([Stock(ticker="AAPL", name="Apple"), Stock(ticker="NVDA", name="Nvidia")])
        await s.commit()
        s.add_all([Portfolio(user_id="u1", ticker="AAPL", quantity=10, avg_cost=100),
                   Portfolio(user_id="u1", ticker="NVDA", quantity=0, avg_cost=0)])
        s.add(UserInvestmentProfile(user_id="u1", risk_tolerance="CONSERVATIVE", risk_tolerance_score=3,
                                    investment_experience="BEGINNER", investment_style="VALUE",
                                    investment_horizon="LONG", preferred_markets="US,HK"))
        await s.commit()
        yield s
    await engine.dispose()


# ---------------------------------------------------------------- advice
def test_parse_tags_and_strip():
    ans = "结论：看多。\n【建议】AAPL|BUY|20|估值合理+回购\n【建议】nvda|sell|5|短线过热\n以上不构成投资建议。"
    tags = advice.parse_answer_tags(ans)
    assert [(t["ticker"], t["direction"], t["horizon_days"]) for t in tags] == [("AAPL", "BUY", 20), ("NVDA", "SELL", 5)]
    assert "【建议】" not in advice.strip_answer_tags(ans)


def test_from_diagnosis_and_judge():
    a = advice.from_diagnosis({"ticker": "aapl", "immediate_action": "逢低买入", "investment_horizon": "1-3月",
                               "current_price": "180.5", "target_price": 200, "core_logic_summary": "x"})
    assert a["direction"] == "BUY" and a["horizon_days"] == 60 and a["price_at"] == 180.5
    assert advice.from_diagnosis({"ticker": "X", "immediate_action": "看不清"}) is None
    assert advice.judge("BUY", 100, 110)[1] is True
    assert advice.judge("SELL", 100, 110)[1] is False
    assert advice.judge("HOLD", 100, 97)[1] is True and advice.judge("HOLD", 100, 90)[1] is False


@pytest.mark.asyncio
async def test_record_dedupe_evaluate_stats(db):
    async def price(t):
        return 100.0
    rows = await advice.record_advice(db, "u1", [{"ticker": "AAPL", "direction": "BUY", "horizon_days": 5}], "agent", price_fn=price)
    again = await advice.record_advice(db, "u1", [{"ticker": "AAPL", "direction": "BUY", "horizon_days": 5}], "agent", price_fn=price)
    assert len(rows) == 1 and again == []
    assert await advice.evaluate_due(db, price) == 0  # not due yet

    async def later(t):
        return 112.0
    n = await advice.evaluate_due(db, later, now=datetime.utcnow() + timedelta(days=6))
    r = (await db.execute(select(AgentAdviceRecord))).scalar_one()
    assert n == 1 and r.status == "evaluated" and r.hit is True and round(r.return_pct, 1) == 12.0
    st = await advice.stats(db, "u1")
    assert st["evaluated"] == 1 and st["hit_rate"] == 1.0


@pytest.mark.asyncio
async def test_chat_records_advice_and_injects_memory(db, monkeypatch):
    async def price(_db, t):
        return 50.0
    monkeypatch.setattr(service, "system_price", price)
    u1 = await db.get(User, "u1")
    llm = FakeLLM(["建议继续持有。\n【建议】AAPL|HOLD|30|基本面稳定"])
    r = await service.chat(db, u1, "AAPL 怎么办", client=llm)
    sys_texts = " ".join(m["content"] for m in llm.calls[0]["messages"] if m["role"] == "system")
    assert "保守" in sys_texts and "AAPL" in sys_texts and "NVDA" in sys_texts  # profile + holdings + watchlist
    assert "【建议】" not in r["answer"] and r["advice"][0]["direction"] == "HOLD"
    rec = (await db.execute(select(AgentAdviceRecord))).scalar_one()
    assert rec.price_at == 50.0 and rec.conversation_id == r["conversation_id"]


# ---------------------------------------------------------------- brief + push
@pytest.mark.asyncio
async def test_generate_brief_once_per_day_and_push(db):
    u1 = await db.get(User, "u1")
    llm = FakeLLM(["### 一句话总览\nAAPL 小涨"])
    b = await brief.generate_brief(db, u1, client=llm)
    assert b.status == "ok" and "AAPL" in b.content and json.loads(b.tickers) == ["AAPL", "NVDA"]
    names = {t["function"]["name"] for t in llm.calls[0]["tools"]}
    assert "run_stock_diagnosis" not in names and "get_portfolio" in names
    assert (await brief.generate_brief(db, u1, client=FakeLLM([]))).id == b.id  # cached for today

    db.add(AgentNotifierConfig(user_id="u1", kind="webhook", url="https://example.com/hook"))
    await db.commit()
    sent = []

    async def fake_send(kind, url, secret, title, md):
        sent.append((kind, url, title))
        return True, "ok"
    assert await brief.push_brief(db, b, send_fn=fake_send) == ["webhook"]
    assert sent[0][1] == "https://example.com/hook" and b.pushed_channels == "webhook"


def test_dingtalk_sign_and_payloads():
    url = notifier.dingtalk_signed_url("https://oapi.dingtalk.com/robot/send?access_token=t", "SEC", ts_ms=1700000000000)
    expect = urllib.parse.quote_plus(base64.b64encode(hmac.new(b"SEC", b"1700000000000\nSEC", hashlib.sha256).digest()).decode())
    assert url.endswith(f"&timestamp=1700000000000&sign={expect}")
    _, p = notifier.build_request("dingtalk", "https://oapi.dingtalk.com/robot/send?access_token=t", None, "今日简报", "hi")
    assert p["msgtype"] == "markdown" and "今日简报" in p["markdown"]["text"]
    assert notifier.validate("dingtalk", "https://evil.com/x", None)
    assert notifier.validate("webhook", "http://insecure", None)
    assert notifier.validate("dingtalk", "https://oapi.dingtalk.com/robot/send?access_token=t", None) is None


# ---------------------------------------------------------------- trial
@pytest.mark.asyncio
async def test_trial_quota_memory_fallback():
    trial._mem.clear()
    res = [await trial.consume_quota("1.2.3.4", limit=2, redis=None, day="d") for _ in range(3)]
    assert [r[0] for r in res] == [True, True, False]
    assert (await trial.consume_quota("5.6.7.8", limit=2, redis=None, day="d"))[0] is True


@pytest.mark.asyncio
async def test_trial_tools_exclude_portfolio(db):
    llm = FakeLLM([{"content": "", "tool_calls": [{"id": "1", "function": {"name": "get_portfolio", "arguments": "{}"}}]},
                   "好的"])
    r = await trial.trial_chat(db, "我的持仓", client=llm)
    names = {t["function"]["name"] for t in llm.calls[0]["tools"]}
    assert names == trial.TRIAL_TOOL_NAMES
    assert r["steps"][0]["ok"] is False  # portfolio refused even if the model asks
    ctx = ToolContext(db=db, user=None, allowed_tools=set(trial.TRIAL_TOOL_NAMES), trial=True)
    ok, text = await execute_tool("run_stock_diagnosis", {"ticker": "AAPL"}, ctx)
    assert ok is False and "不可用" in text
