"""Unit tests for the P1 agent: loop, tool scoping, MCP protocol."""
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "x" * 40)

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent import tools as agent_tools
from app.agent.llm import LLMError
from app.agent.loop import run_agent
from app.agent.tools import ToolContext, execute_tool, truncate_result

USER = SimpleNamespace(id="user-a", preferred_data_source="AUTO", preferred_ai_model="x")


class FakeLLM:
    """Scripted chat client: returns queued messages, records calls."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    async def chat(self, messages, tools=None):
        self.calls.append({"messages": [dict(m) for m in messages], "tools": tools})
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def tool_call(name, args, cid="c1"):
    return {"role": "assistant", "content": "", "tool_calls": [
        {"id": cid, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}


@pytest.fixture
def fake_quote(monkeypatch):
    calls = []

    async def handler(ctx, args):
        calls.append((ctx.user.id, args))
        ctx.add_source("quote")
        return {"ticker": args["ticker"].upper(), "current_price": 123.4}

    monkeypatch.setattr(agent_tools.TOOL_MAP["get_quote"], "handler", handler)
    return calls


@pytest.mark.asyncio
async def test_loop_calls_tool_then_answers(fake_quote):
    llm = FakeLLM([tool_call("get_quote", {"ticker": "nvda"}), {"role": "assistant", "content": "NVDA 现价 123.4"}])
    res = await run_agent(llm, ToolContext(db=AsyncMock(), user=USER), "NVDA 多少钱")
    assert res.answer == "NVDA 现价 123.4"
    assert [s.tool for s in res.steps] == ["get_quote"] and res.steps[0].ok
    assert fake_quote == [("user-a", {"ticker": "nvda"})]
    tool_msg = llm.calls[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and "123.4" in tool_msg["content"]
    assert res.sources and res.mode == "tools"
    assert llm.calls[0]["tools"] and any(t["function"]["name"] == "get_portfolio" for t in llm.calls[0]["tools"])


@pytest.mark.asyncio
async def test_loop_respects_max_steps(fake_quote):
    llm = FakeLLM([tool_call("get_quote", {"ticker": "AAPL"})] * 3 + [{"content": "final"}])
    res = await run_agent(llm, ToolContext(db=AsyncMock(), user=USER), "q", max_steps=3)
    assert res.stopped_reason == "max_steps" and res.answer == "final"
    assert len(res.steps) == 3 and llm.calls[-1]["tools"] is None


@pytest.mark.asyncio
async def test_loop_unknown_tool_and_bad_args_are_reported_not_raised():
    llm = FakeLLM([
        {"content": "", "tool_calls": [{"id": "1", "function": {"name": "drop_db", "arguments": "{}"}},
                                       {"id": "2", "function": {"name": "get_quote", "arguments": "{not json"}}]},
        {"content": "ok"},
    ])
    res = await run_agent(llm, ToolContext(db=AsyncMock(), user=USER), "q")
    assert res.answer == "ok"
    assert [s.ok for s in res.steps] == [False, False]


@pytest.mark.asyncio
async def test_loop_no_tools_fallback(fake_quote):
    llm = FakeLLM([LLMError("tools not supported", status=400, tools_unsupported=True), {"content": "fallback answer"}])
    res = await run_agent(llm, ToolContext(db=AsyncMock(), user=USER), "看下 TSLA")
    assert res.mode == "no_tools_fallback" and res.answer == "fallback answer"
    assert llm.calls[1]["tools"] is None
    assert any(s.tool == "get_quote" and s.arguments == {"ticker": "TSLA"} for s in res.steps)


@pytest.mark.asyncio
async def test_loop_llm_error_is_graceful():
    llm = FakeLLM([LLMError("HTTP 500")])
    res = await run_agent(llm, ToolContext(db=AsyncMock(), user=USER), "q")
    assert res.mode == "error" and "暂时不可用" in res.answer


@pytest.mark.asyncio
async def test_tool_scoping_strips_user_id_and_requires_user(monkeypatch):
    seen = {}

    async def handler(ctx, args):
        seen.update(args)
        return {"uid": ctx.user.id}

    monkeypatch.setattr(agent_tools.TOOL_MAP["get_portfolio"], "handler", handler)
    ok, text = await execute_tool("get_portfolio", {"user_id": "victim"}, ToolContext(db=AsyncMock(), user=USER))
    assert ok and "user_id" not in seen and json.loads(text) == {"uid": "user-a"}
    ok, text = await execute_tool("get_portfolio", {}, ToolContext(db=AsyncMock(), user=None))
    assert not ok and "未认证" in text


@pytest.mark.asyncio
async def test_get_portfolio_uses_current_user_only():
    captured = []

    class FakeUC:
        def __init__(self, db, user):
            captured.append(user.id)

        async def execute(self, **kw):
            return []

    class FakeSummary(FakeUC):
        async def execute(self):
            return {"total_market_value": 0, "holdings": []}

    with patch("app.application.portfolio.query_portfolio.GetPortfolioUseCase", FakeUC), \
         patch("app.application.portfolio.query_portfolio.GetPortfolioSummaryUseCase", FakeSummary):
        ok, text = await execute_tool("get_portfolio", {}, ToolContext(db=AsyncMock(), user=USER))
    assert ok and captured == ["user-a", "user-a"]


@pytest.mark.asyncio
async def test_invalid_ticker_rejected():
    ok, text = await execute_tool("get_quote", {"ticker": "AAPL; DROP TABLE"}, ToolContext(db=AsyncMock(), user=USER))
    assert not ok and "ticker" in text


@pytest.mark.asyncio
async def test_tool_exception_is_contained(monkeypatch):
    async def boom(ctx, args):
        raise RuntimeError("secret internals")

    monkeypatch.setattr(agent_tools.TOOL_MAP["macro_snapshot"], "handler", boom)
    db = AsyncMock()
    ok, text = await execute_tool("macro_snapshot", {}, ToolContext(db=db, user=USER))
    assert not ok and "secret internals" not in text and "RuntimeError" in text
    db.rollback.assert_awaited()


def test_truncate_result_limits_size():
    text = truncate_result({"x": "a" * 50000}, max_chars=1000)
    assert len(text) <= 1000 and "truncated" in text


def test_token_hashing():
    from app.agent.service import generate_token, hash_token
    t = generate_token()
    assert t.startswith("asa_") and len(hash_token(t)) == 64 and hash_token(t) != t


# ------------------------------------------------------------------ MCP

@pytest.fixture
def mcp_client(monkeypatch, fake_quote):
    from app.core.database import get_db
    from app.mcp import server

    async def fake_auth(db, token):
        return USER if token == "asa_good" else None

    monkeypatch.setattr(server.service, "get_user_by_api_token", fake_auth)
    monkeypatch.setattr("app.api.deps._load_user_data_source_config", lambda u: None)
    app = FastAPI()
    app.include_router(server.router)

    async def _db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = _db
    return TestClient(app)


H = {"Authorization": "Bearer asa_good", "Accept": "application/json, text/event-stream"}


def test_mcp_requires_token(mcp_client):
    r = mcp_client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert r.status_code == 401
    r = mcp_client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers={"Authorization": "Bearer asa_bad"})
    assert r.status_code == 401


def test_mcp_initialize(mcp_client):
    r = mcp_client.post("/mcp", headers=H, json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                                  "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}})
    assert r.status_code == 200 and r.headers.get("mcp-session-id")
    res = r.json()["result"]
    assert res["protocolVersion"] == "2025-06-18" and "tools" in res["capabilities"]
    r = mcp_client.post("/mcp", headers=H, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert r.status_code == 202


def test_mcp_tools_list(mcp_client):
    r = mcp_client.post("/mcp", headers=H, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = {t["name"] for t in r.json()["result"]["tools"]}
    assert {"get_quote", "get_kline_and_technicals", "get_fundamentals", "search_news", "get_portfolio",
            "run_stock_diagnosis", "macro_snapshot", "ask_stock_agent"} <= names
    for t in r.json()["result"]["tools"]:
        assert t["inputSchema"]["type"] == "object" and t["annotations"]["readOnlyHint"] is True


def test_mcp_tools_call(mcp_client):
    r = mcp_client.post("/mcp", headers=H, json={"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                                  "params": {"name": "get_quote", "arguments": {"ticker": "AAPL"}}})
    res = r.json()["result"]
    assert not res.get("isError") and "123.4" in res["content"][0]["text"] and "不构成投资建议" in res["content"][0]["text"]
    r = mcp_client.post("/mcp", headers=H, json={"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "nope"}})
    assert r.json()["error"]["code"] == -32602
    r = mcp_client.post("/mcp", headers=H, json={"jsonrpc": "2.0", "id": 5, "method": "foo"})
    assert r.json()["error"]["code"] == -32601


def test_mcp_sse_only_accept_and_parse_error(mcp_client):
    r = mcp_client.post("/mcp", headers={**H, "Accept": "text/event-stream"}, json={"jsonrpc": "2.0", "id": 1, "method": "ping"})
    assert r.headers["content-type"].startswith("text/event-stream") and r.text.startswith("event: message")
    r = mcp_client.post("/mcp", headers={**H, "Content-Type": "application/json"}, content=b"{bad")
    assert r.status_code == 400 and r.json()["error"]["code"] == -32700
