import pytest
import json
from unittest.mock import patch, MagicMock
from app.services.ai_service import AIService
from app.services.integrations.ai.provider_router import ProviderRouter


@pytest.mark.asyncio
async def test_resolve_api_key_with_user_config():
    """API key resolution should prefer user-level api_configs."""
    user = MagicMock()
    user.id = "test-user"
    user.api_configs = json.dumps({
        "siliconflow": {"base_url": "https://custom.siliconflow.ai/v1"}
    })
    user.api_key_siliconflow = "encrypted_key"

    with patch("app.core.security.decrypt_api_key", return_value="decrypted_key"):
        api_key, custom_url = await AIService._resolve_api_key("siliconflow", user)
        assert api_key == "decrypted_key"
        assert custom_url == "https://custom.siliconflow.ai/v1"


@pytest.mark.asyncio
async def test_resolve_api_key_fallback_to_system():
    """When user has no key configured, fall back to system env var."""
    user = MagicMock()
    user.id = "test-user"
    user.api_configs = None
    user.api_key_siliconflow = None

    with patch("app.core.config.settings.SILICONFLOW_API_KEY", "system_key"):
        api_key, custom_url = await AIService._resolve_api_key("siliconflow", user)
        assert api_key == "system_key"
        assert custom_url is None


@pytest.mark.asyncio
async def test_test_connection_success():
    """test_connection should return success when call_provider succeeds."""
    with patch.object(ProviderRouter, "call_provider", return_value="pong"):
        success, message = await AIService.test_connection("siliconflow", "test-key", "https://api.test.com")
        assert success is True
        assert message == "连接成功"


@pytest.mark.asyncio
async def test_test_connection_failure():
    """test_connection should return failure with error details when call_provider raises."""
    with patch.object(ProviderRouter, "call_provider", side_effect=Exception("Invalid Key")):
        success, message = await AIService.test_connection("siliconflow", "wrong-key")
        assert success is False
        assert "Invalid Key" in message
