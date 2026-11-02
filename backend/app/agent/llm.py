"""
Agent LLM layer: resolve which OpenAI-compatible endpoint to use for a user,
and perform chat-completions calls with tool definitions.

Resolution order (keeps BYOK working, reuses existing resolver):
  1. User custom model (UserAIModel) matching user.preferred_ai_model
  2. User's own provider credential for the preferred model's provider
     (ModelResolver.resolve_api_key, only if it differs from the system env key)
  3. System relay from env: LLM_BASE_URL / LLM_MODEL / LLM_API_KEY (致拓 relay)
  4. Existing system provider_configs + env keys (ModelResolver)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional, Protocol

import httpx

from app.core.config import settings
from app.services.integrations.ai.model_resolver import ModelResolver

logger = logging.getLogger(__name__)


@dataclass
class LLMTarget:
    base_url: str
    model: str
    api_key: str
    source: str  # user_model | user_credential | system_relay | system_provider

    def public(self) -> dict:
        return {"model": self.model, "source": self.source}


class LLMError(Exception):
    def __init__(self, message: str, status: int | None = None, tools_unsupported: bool = False):
        super().__init__(message)
        self.status = status
        self.tools_unsupported = tools_unsupported


class ChatClient(Protocol):
    async def chat(self, messages: list[dict], tools: Optional[list[dict]] = None) -> dict: ...


_TOOL_ERR_HINTS = ("tool", "function", "not support")


class OpenAIChatClient:
    """Minimal OpenAI-compatible /chat/completions client with tool support."""

    def __init__(self, target: LLMTarget, timeout: int | None = None):
        self.target = target
        self.timeout = timeout or settings.AGENT_LLM_TIMEOUT_SECONDS

    async def chat(self, messages: list[dict], tools: Optional[list[dict]] = None) -> dict:
        payload: dict[str, Any] = {"model": self.target.model, "messages": messages, "temperature": 0.2}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        url = f"{self.target.base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self.target.api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=10.0), trust_env=True) as client:
                resp = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as e:
            raise LLMError(f"LLM timeout after {self.timeout}s") from e
        except httpx.HTTPError as e:
            raise LLMError(f"LLM transport error: {e.__class__.__name__}") from e
        if resp.status_code >= 400:
            body = resp.text[:300]
            unsupported = bool(tools) and resp.status_code in (400, 404, 422) and any(
                h in body.lower() for h in _TOOL_ERR_HINTS
            )
            raise LLMError(f"LLM HTTP {resp.status_code}: {body}", status=resp.status_code, tools_unsupported=unsupported)
        try:
            data = resp.json()
            return data["choices"][0]["message"]
        except Exception as e:  # malformed response
            raise LLMError(f"Malformed LLM response: {resp.text[:200]}") from e


async def resolve_agent_llm(user, db) -> Optional[LLMTarget]:
    model_key = getattr(user, "preferred_ai_model", None) or settings.DEFAULT_AI_MODEL

    # 1. user custom model (BYOK)
    if user is not None and db is not None:
        try:
            um = await ModelResolver.get_user_ai_model(model_key, user.id, db)
            if um and um.encrypted_api_key:
                from app.core import security
                return LLMTarget(
                    base_url=ModelResolver.normalize_user_model_base_url(um.base_url),
                    model=um.model_id,
                    api_key=security.decrypt_api_key(um.encrypted_api_key),
                    source="user_model",
                )
        except Exception as e:
            logger.warning(f"agent: user model lookup failed: {e}")

    model_config = await ModelResolver.get_model_config(model_key, db)
    providers: list[dict] = []
    if db is not None:
        try:
            providers = await ModelResolver.get_provider_list(db)
        except Exception as e:
            logger.warning(f"agent: provider list unavailable: {e}")
    provider_urls = {p["provider_key"]: p["base_url"] for p in providers}

    # 2. user's own credential for the preferred provider
    if user is not None:
        try:
            key, url = await ModelResolver.resolve_api_key(model_config.provider, user, db)
            sys_key, _ = await ModelResolver.resolve_api_key(model_config.provider, None, None)
            base = url or provider_urls.get(model_config.provider)
            if key and key != sys_key and base:
                return LLMTarget(base, model_config.model_id, key, "user_credential")
        except Exception as e:
            logger.warning(f"agent: user credential lookup failed: {e}")

    # 3. system relay
    if settings.LLM_BASE_URL and settings.LLM_API_KEY and settings.LLM_MODEL:
        return LLMTarget(settings.LLM_BASE_URL, settings.LLM_MODEL, settings.LLM_API_KEY, "system_relay")

    # 4. existing system providers
    ordered = sorted(providers, key=lambda p: 0 if p["provider_key"] == model_config.provider else 1)
    for p in ordered:
        key, url = await ModelResolver.resolve_api_key(p["provider_key"], None, None)
        if key:
            model_id = (
                model_config.model_id
                if p["provider_key"] == model_config.provider
                else await ModelResolver.get_default_model_for_provider(p["provider_key"], db)
            )
            return LLMTarget(url or p["base_url"], model_id, key, "system_provider")
    return None
