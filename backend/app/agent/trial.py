"""Zero-friction trial (/try): unauthenticated, read-only public-market tools, per-IP daily quota."""
from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Optional

from app.agent.llm import ChatClient, LLMTarget, OpenAIChatClient
from app.agent.loop import AgentResult, run_agent
from app.agent.tools import TRIAL_TOOL_NAMES, ToolContext
from app.agent.advice import strip_answer_tags
from app.core.config import settings

TRIAL_SYSTEM = ("当前是未登录的试用模式：只能使用公开行情/新闻/宏观工具，无法查看任何用户持仓，"
                "也不能做深度诊断。回答简洁（300 字内），结尾可提示注册后可获得持仓简报与建议复盘。")

_mem: dict[str, tuple[int, float]] = {}  # fallback when Redis is unavailable (single process)


def client_ip(request) -> str:
    # Nginx sets X-Real-IP; X-Forwarded-For first hop as fallback. (Both are trusted only behind our proxy.)
    h = request.headers
    ip = (h.get("x-real-ip") or (h.get("x-forwarded-for") or "").split(",")[0]).strip()
    return ip or (request.client.host if request.client else "unknown")


async def consume_quota(ip: str, limit: Optional[int] = None, redis=None, day: Optional[str] = None) -> tuple[bool, int]:
    """Returns (allowed, remaining)."""
    from app.agent.brief import today_cn

    limit = settings.AGENT_TRIAL_DAILY_LIMIT if limit is None else limit
    key = f"agent:trial:{day or today_cn()}:{ip}"
    if redis is None:
        from app.core.redis_client import get_redis
        redis = await get_redis()
    if redis is not None:
        n = await redis.incr(key)
        if n == 1:
            await redis.expire(key, 26 * 3600)
    else:
        now = time.time()
        n0, exp = _mem.get(key, (0, now + 26 * 3600))
        n = n0 + 1
        _mem[key] = (n, exp)
        for k in [k for k, (_, e) in _mem.items() if e < now]:
            _mem.pop(k, None)
    return n <= limit, max(0, limit - n)


def trial_target() -> Optional[LLMTarget]:
    # Trial only uses the system relay — never any user's BYOK key.
    if settings.LLM_BASE_URL and settings.LLM_API_KEY and settings.LLM_MODEL:
        return LLMTarget(settings.LLM_BASE_URL, settings.LLM_MODEL, settings.LLM_API_KEY, "system_relay")
    return None


async def trial_chat(db, message: str, client: Optional[ChatClient] = None) -> dict:
    if client is None:
        target = trial_target()
        if target is None:
            r = AgentResult("试用暂不可用：系统未配置默认模型。", mode="error", stopped_reason="llm_error")
            return r.as_dict()
        client = OpenAIChatClient(target)
    guest = SimpleNamespace(id=None, preferred_data_source="AUTO", preferred_ai_model=None)
    ctx = ToolContext(db=db, user=guest, allowed_tools=set(TRIAL_TOOL_NAMES), trial=True)
    result = await run_agent(client, ctx, message, [], max_steps=settings.AGENT_TRIAL_MAX_STEPS, extra_system=TRIAL_SYSTEM)
    result.answer = strip_answer_tags(result.answer)
    return result.as_dict()
