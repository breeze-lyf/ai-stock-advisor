"""Tool-calling agent loop over OpenAI-compatible chat completions."""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from app.agent.llm import ChatClient, LLMError
from app.agent.tools import TOOLS, ToolContext, execute_tool

logger = logging.getLogger(__name__)

DISCLAIMER = "以上内容由 AI 基于公开数据生成，仅供研究参考，不构成投资建议。"

SYSTEM_PROMPT = """你是「AI 智能投顾」的投研助理智能体，服务对象是本系统的注册用户。
工作方式：
- 先判断需要哪些数据，再调用工具获取真实数据；不要凭记忆编造价格、财务数据或新闻。
- 涉及持仓的问题调用 get_portfolio（只能查看当前用户自己的持仓）。
- run_stock_diagnosis 耗时较长，只在用户明确要深度分析/诊断时调用。
- 工具报错或无数据时，如实说明缺失项，不要猜测。
- 用简体中文回答，结论先行，给出关键数字、依据与风险；注明数据来源与时间。
- 你不做交易执行，不承诺收益。回答末尾附上：「""" + DISCLAIMER + "」"

_TICKER_HINT = re.compile(r"\b(\d{6}(?:\.S[SZH])?|\d{4,5}\.HK|[A-Z]{1,5})\b")


@dataclass
class AgentStep:
    tool: str
    arguments: dict
    ok: bool
    duration_ms: int
    result_preview: str

    def as_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class AgentResult:
    answer: str
    steps: list[AgentStep] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    mode: str = "tools"  # tools | no_tools_fallback | error
    stopped_reason: str = "final"  # final | max_steps | llm_error

    def as_dict(self) -> dict:
        return {
            "answer": self.answer,
            "steps": [s.as_dict() for s in self.steps],
            "sources": self.sources,
            "mode": self.mode,
            "stopped_reason": self.stopped_reason,
        }


def _safe_args(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        v = json.loads(raw or "{}")
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


async def _run_tool(name: str, args: dict, ctx: ToolContext, steps: list[AgentStep]) -> str:
    t0 = time.monotonic()
    ok, text = await execute_tool(name, dict(args), ctx)
    steps.append(AgentStep(name, args, ok, int((time.monotonic() - t0) * 1000), text[:500]))
    return text


async def _fallback_no_tools(client: ChatClient, messages: list[dict], ctx: ToolContext, steps: list[AgentStep]) -> str:
    """Model doesn't support tool-calling: prefetch quotes for tickers mentioned, then single call."""
    user_text = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "") or ""
    context_parts = []
    for tk in list(dict.fromkeys(_TICKER_HINT.findall(user_text.upper())))[:3]:
        if len(tk) <= 1 or tk in {"AI", "A", "ETF", "PE", "MACD", "RSI", "K"}:
            continue
        text = await _run_tool("get_quote", {"ticker": tk}, ctx, steps)
        context_parts.append(f"[get_quote {tk}] {text}")
    if any(k in user_text for k in ("持仓", "组合", "portfolio")):
        context_parts.append(f"[get_portfolio] {await _run_tool('get_portfolio', {}, ctx, steps)}")
    msgs = list(messages)
    if context_parts:
        msgs.append({"role": "system", "content": "已为你预取的数据（模型不支持工具调用）：\n" + "\n".join(context_parts)})
    msg = await client.chat(msgs, tools=None)
    return msg.get("content") or ""


async def run_agent(
    client: ChatClient,
    ctx: ToolContext,
    user_message: str,
    history: Optional[list[dict]] = None,
    max_steps: int = 8,
) -> AgentResult:
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in (history or [])[-12:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": str(h["content"])[:4000]})
    messages.append({"role": "user", "content": user_message})
    tool_schemas = [t.openai_schema() for t in TOOLS]
    steps: list[AgentStep] = []

    for _ in range(max_steps):
        try:
            msg = await client.chat(messages, tools=tool_schemas)
        except LLMError as e:
            if e.tools_unsupported:
                logger.info("agent: model rejected tools, using no-tools fallback")
                try:
                    answer = await _fallback_no_tools(client, messages, ctx, steps)
                    return AgentResult(answer, steps, ctx.sources, mode="no_tools_fallback")
                except LLMError as e2:
                    e = e2
            logger.warning(f"agent llm error: {e}")
            return AgentResult(f"AI 服务暂时不可用：{e}", steps, ctx.sources, mode="error", stopped_reason="llm_error")

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            return AgentResult(msg.get("content") or "", steps, ctx.sources)

        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": tool_calls})
        for tc in tool_calls:
            fn = tc.get("function") or {}
            name = fn.get("name") or ""
            args = _safe_args(fn.get("arguments"))
            text = await _run_tool(name, args, ctx, steps)
            messages.append({"role": "tool", "tool_call_id": tc.get("id") or name, "content": text})

    # Step budget exhausted: ask for a final answer without tools.
    messages.append({"role": "system", "content": "工具调用次数已达上限，请基于已获取的数据直接给出最终回答。"})
    try:
        msg = await client.chat(messages, tools=None)
        return AgentResult(msg.get("content") or "", steps, ctx.sources, stopped_reason="max_steps")
    except LLMError as e:
        return AgentResult(f"AI 服务暂时不可用：{e}", steps, ctx.sources, mode="error", stopped_reason="llm_error")
