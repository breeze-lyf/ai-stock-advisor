"""
AI Provider Client — 传输层
职责：封装与 AI 供应商的 HTTP 通信（OpenAI 兼容接口）
"""
import asyncio
import logging
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)
# AI 调用专用 logger
ai_call_logger = logging.getLogger("app.ai_calls")

# 单次 LLM 调用的硬性上限（秒），防止任何供应商配置过大导致 worker 长期挂死
_MAX_LLM_CALL_TIMEOUT = 180


def infer_provider_key(base_url: Optional[str] = None, provider_hint: Optional[str] = None) -> str:
    """根据 base_url / provider_hint 推断供应商标识"""
    hint = (provider_hint or "").strip().lower()
    url = (base_url or "").strip().lower()

    combined = f"{hint} {url}"
    if any(token in combined for token in ["gemini", "googleapis.com", "generativelanguage"]):
        return "gemini"
    if "siliconflow" in combined:
        return "siliconflow"
    if "deepseek" in combined:
        return "deepseek"
    if "dashscope" in combined or "aliyuncs.com" in combined or "qwen" in combined:
        return "dashscope"
    if "minimax" in combined:
        return "minimax"
    if "anthropic" in combined or "claude" in combined:
        return "anthropic"
    if "openrouter" in combined:
        return "openrouter"
    return "openai-compatible"


def _format_exception(e: Exception) -> str:
    msg = str(e).strip()
    return msg if msg else e.__class__.__name__


async def call_provider(
    provider_config: Any,
    model_id: str,
    prompt: str,
    api_key: str,
    custom_url: Optional[str] = None,
    require_json: bool = True,
) -> str:
    """
    通用供应商调用器（OpenAI 兼容接口）。
    纯 HTTP 传输层 — 无数据库依赖。
    总调用时间受 _MAX_LLM_CALL_TIMEOUT 硬性上限保护。
    """
    call_start = time.monotonic()
    provider_key = provider_config.provider_key

    ai_call_logger.info(
        f"[PROMPT] {provider_key}/{model_id}",
        extra={
            "provider": provider_key,
            "model": model_id,
            "prompt_len": len(prompt),
            "prompt": prompt,
            "phase": "request",
        },
    )
    logger.info(f"[AI] 调用 {provider_key}/{model_id} (prompt {len(prompt)}字符)")

    base_url = custom_url or provider_config.base_url
    _db_timeout = provider_config.timeout_seconds or 120
    # 以数据库配置为准，最小 30s；同时不超过硬性上限
    timeout = min(max(_db_timeout, 30), _MAX_LLM_CALL_TIMEOUT)

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async def _do_call(use_json: bool):
        payload: dict = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }
        if use_json:
            payload["response_format"] = {"type": "json_object"}

        client_kwargs = {
            "timeout": httpx.Timeout(timeout, connect=10.0),
            "trust_env": True,
        }
        t_send = time.monotonic()
        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.post(url, json=payload, headers=headers)
        t_recv = time.monotonic()
        ai_call_logger.debug(
            f"[HTTP] {provider_key} http={response.status_code}",
            extra={
                "provider": provider_key,
                "phase": "http",
                "http_status": response.status_code,
                "request_s": round(t_recv - t_send, 3),
                "total_s": round(t_recv - call_start, 3),
            },
        )
        return response

    try:
        response = await asyncio.wait_for(_do_call(use_json=require_json), timeout=_MAX_LLM_CALL_TIMEOUT)
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - call_start
        ai_call_logger.error(
            f"[TIMEOUT] {provider_key}: hard limit {_MAX_LLM_CALL_TIMEOUT}s exceeded",
            extra={"provider": provider_key, "phase": "timeout", "total_s": round(elapsed, 3)},
        )
        logger.warning(f"[AI] 请求达到硬性超时上限 ({provider_key}, {_MAX_LLM_CALL_TIMEOUT}s)")
        raise httpx.ReadTimeout(f"LLM call exceeded hard timeout of {_MAX_LLM_CALL_TIMEOUT}s", request=None)
    except httpx.TimeoutException as e:
        elapsed = time.monotonic() - call_start
        ai_call_logger.error(
            f"[TIMEOUT] {provider_key}: {_format_exception(e)}",
            extra={"provider": provider_key, "phase": "timeout", "total_s": round(elapsed, 3)},
        )
        logger.warning(f"[AI] 请求超时 ({provider_key}, {elapsed:.1f}s)")
        raise

    if response.status_code == 400 and require_json:
        error_data: dict = {}
        try:
            if "application/json" in response.headers.get("content-type", ""):
                error_data = response.json()
        except Exception:
            pass
        error_msg = error_data.get("error", {}).get("message", "").lower()
        if "response_format" in error_msg or "json_object" in error_msg:
            logger.info(f"[AI] 降级重试 (no json_object)...")
            response = await asyncio.wait_for(_do_call(use_json=False), timeout=_MAX_LLM_CALL_TIMEOUT)

    if response.status_code != 200:
        error_text = response.text
        elapsed = time.monotonic() - call_start
        ai_call_logger.error(
            f"[FAIL] {provider_key} HTTP {response.status_code}",
            extra={
                "provider": provider_key,
                "phase": "error",
                "http_status": response.status_code,
                "response_body": error_text[:500],
                "total_s": round(elapsed, 3),
            },
        )
        logger.warning(f"[AI] {provider_key} 返回 {response.status_code} ({elapsed:.1f}s)")
        if response.status_code in [401, 402]:
            raise ValueError(f"Auth Error: {response.status_code}")
        if response.status_code == 404:
            raise RuntimeError(
                f"{provider_key} HTTP 404: 模型未找到 — 请确认模型 ID「{model_id}」"
                f" 在该供应商的推理 API 中已可用（新上架模型可能存在延迟，或需账户充值后才可调用）"
            )
        raise RuntimeError(
            f"{provider_key} HTTP {response.status_code}: {(error_text or '').strip()[:300]}"
        )

    result = response.json()
    content = result["choices"][0]["message"]["content"]
    elapsed = time.monotonic() - call_start
    ai_call_logger.info(
        f"[DONE] {provider_key}/{model_id}",
        extra={
            "provider": provider_key,
            "model": model_id,
            "phase": "done",
            "total_s": round(elapsed, 3),
            "response_len": len(content),
            "response": content,
        },
    )
    logger.info(f"[AI] {provider_key} 完成 ✔  {elapsed:.1f}s | {len(content)}字符")
    return content
