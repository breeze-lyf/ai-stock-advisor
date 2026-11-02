"""
MCP server — Streamable HTTP transport (protocol 2025-06-18), JSON-RPC 2.0.
Stateless, JSON responses (SSE single-event if client only accepts SSE).
Auth: personal API token (Authorization: Bearer asa_...) → per-user scoping.
Modeled after boss-agent/server/mcp.js.
"""
from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import service
from app.agent.loop import DISCLAIMER
from app.agent.tools import TOOL_MAP, TOOLS, ToolContext, execute_tool
from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"]
MAX_BODY = 100_000
CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Accept, Authorization, Mcp-Session-Id, MCP-Protocol-Version",
    "Access-Control-Expose-Headers": "Mcp-Session-Id",
    "Cache-Control": "no-store",
}

ASK_TOOL = {
    "name": "ask_stock_agent",
    "title": "问投研智能体",
    "description": "用自然语言提问（如「帮我看下 NVDA 的技术面」「我的持仓今天怎么样」），智能体会自动调用行情/新闻/基本面/持仓工具后给出回答与来源。",
    "inputSchema": {"type": "object", "properties": {
        "question": {"type": "string", "description": "问题"},
        "conversation_id": {"type": "string", "description": "可选，延续之前的会话"},
    }, "required": ["question"]},
    "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": True},
}


def tool_list() -> list[dict]:
    return [t.mcp_schema() for t in TOOLS] + [ASK_TOOL]


def _err(msg: str) -> dict:
    return {"content": [{"type": "text", "text": msg}], "isError": True}


async def call_tool(name: str, args: dict, db, user) -> dict:
    if name == "ask_stock_agent":
        q = (args.get("question") or "").strip()
        if not q:
            return _err("请提供 question")
        try:
            r = await service.chat(db, user, q[:4000], args.get("conversation_id"), channel="mcp")
        except LookupError:
            return _err("conversation_id 不存在")
        text = r["answer"]
        if r.get("sources"):
            text += "\n\n来源：\n" + "\n".join(f"- {s['title']}" + (f" {s['url']}" if s.get("url") else "") for s in r["sources"][:10])
        return {"content": [{"type": "text", "text": text}],
                "structuredContent": {"conversation_id": r["conversation_id"], "steps": r["steps"], "sources": r["sources"], "mode": r["mode"]}}
    ctx = ToolContext(db=db, user=user)
    ok, text = await execute_tool(name, args, ctx)
    if not ok:
        return {"content": [{"type": "text", "text": text}], "isError": True}
    return {"content": [{"type": "text", "text": text + "\n\n" + DISCLAIMER}]}


async def handle_message(m, db, user):
    if not isinstance(m, dict) or m.get("jsonrpc") != "2.0" or not isinstance(m.get("method"), str):
        return {"jsonrpc": "2.0", "id": (m or {}).get("id") if isinstance(m, dict) else None,
                "error": {"code": -32600, "message": "Invalid Request"}}
    is_note = "id" not in m
    mid = m.get("id")
    method = m["method"]
    params = m.get("params") or {}

    def ok(result):
        return None if is_note else {"jsonrpc": "2.0", "id": mid, "result": result}

    def error(code, msg):
        return None if is_note else {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": msg}}

    try:
        if method == "initialize":
            v = params.get("protocolVersion")
            return ok({
                "protocolVersion": v if v in VERSIONS else VERSIONS[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "ai-stock-advisor", "title": "AI 智能投顾", "version": "0.1.0"},
                "instructions": "AI 智能投顾投研工具：行情、K线技术面、基本面、新闻、宏观、我的持仓（只读）与单股 AI 诊断。" + DISCLAIMER,
            })
        if method == "ping":
            return ok({})
        if method == "tools/list":
            return ok({"tools": tool_list()})
        if method == "tools/call":
            name = params.get("name")
            if name not in TOOL_MAP and name != "ask_stock_agent":
                return error(-32602, f"Unknown tool: {name}")
            args = params.get("arguments") or {}
            if not isinstance(args, dict):
                return error(-32602, "arguments must be an object")
            try:
                return ok(await call_tool(name, args, db, user))
            except Exception:
                logger.exception("mcp tool call failed")
                return ok(_err("工具执行失败"))
        if method.startswith("notifications/"):
            return None
        return error(-32601, "Method not found")
    except Exception:
        logger.exception("mcp internal error")
        return error(-32603, "Internal error")


def _bearer(request: Request) -> str:
    auth = request.headers.get("authorization") or ""
    return auth[7:].strip() if auth.lower().startswith("bearer ") else ""


@router.options("/mcp")
async def mcp_options():
    return Response(status_code=204, headers=CORS)


@router.delete("/mcp")
async def mcp_delete():
    return Response(status_code=200, headers=CORS)


@router.get("/mcp")
async def mcp_get():
    # No server-initiated SSE stream in this stateless server.
    return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": "Method not allowed; use POST"}},
                        status_code=405, headers={**CORS, "Allow": "POST, DELETE, OPTIONS"})


@router.post("/mcp")
async def mcp_post(request: Request, db: AsyncSession = Depends(get_db)):
    user = await service.get_user_by_api_token(db, _bearer(request))
    if user is None:
        return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32001, "message": "Unauthorized: invalid or missing API token"}},
                            status_code=401, headers={**CORS, "WWW-Authenticate": 'Bearer realm="mcp"'})
    from app.api.deps import _load_user_data_source_config
    _load_user_data_source_config(user)

    raw = await request.body()
    if len(raw) > MAX_BODY:
        return Response(status_code=413, headers=CORS)
    try:
        body = json.loads(raw)
    except Exception:
        return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
                            status_code=400, headers=CORS)
    batch = isinstance(body, list)
    msgs = body if batch else [body]
    results = [r for r in [await handle_message(m, db, user) for m in msgs] if r is not None]
    headers = dict(CORS)
    if any(isinstance(m, dict) and m.get("method") == "initialize" for m in msgs):
        headers["Mcp-Session-Id"] = str(uuid.uuid4())
    if not results:
        return Response(status_code=202, headers=headers)
    payload = json.dumps(results if batch else results[0], ensure_ascii=False, default=str)
    accept = request.headers.get("accept") or ""
    if "text/event-stream" in accept and "application/json" not in accept:
        return Response(f"event: message\ndata: {payload}\n\n", media_type="text/event-stream", headers=headers)
    return Response(payload, media_type="application/json; charset=utf-8", headers=headers)
