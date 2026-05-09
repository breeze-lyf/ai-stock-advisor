"""
AI Provider Client — 已废弃，保留向后兼容。
请使用 app.services.ai_provider 中的 OpenAICompatibleProvider。
"""
import warnings
from typing import Any, Optional

from app.services.ai_provider import OpenAICompatibleProvider

warnings.warn(
    "ai_provider_client is deprecated; use ai_provider.OpenAICompatibleProvider instead",
    DeprecationWarning,
    stacklevel=2,
)


async def call_provider(
    provider_config: Any,
    model_id: str,
    prompt: str,
    api_key: str,
    custom_url: Optional[str] = None,
    require_json: bool = True,
    max_tokens: Optional[int] = None,
    extra_params: Optional[dict] = None,
) -> str:
    """已废弃 — 委托给 OpenAICompatibleProvider。"""
    provider = OpenAICompatibleProvider(default_timeout=getattr(provider_config, "timeout_seconds", 120))
    return await provider.complete(
        prompt=prompt,
        model_id=model_id,
        api_key=api_key,
        base_url=custom_url or provider_config.base_url,
        provider_key=provider_config.provider_key,
        require_json=require_json,
        max_tokens=max_tokens,
        extra_params=extra_params,
    )
