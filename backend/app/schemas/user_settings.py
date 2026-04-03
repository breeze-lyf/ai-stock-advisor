from __future__ import annotations
from typing import Literal

from pydantic import BaseModel, ConfigDict
from app.core.config import settings


class ApiConfig(BaseModel):
    api_key: str | None = None
    base_url: str | None = None


class UserProviderCredentialInput(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    is_enabled: bool | None = None


class UserProviderCredentialResponse(BaseModel):
    has_key: bool
    base_url: str | None = None
    is_enabled: bool


class AIModelConfigCreate(BaseModel):
    display_name: str
    provider_note: str | None = None
    model_id: str
    api_key: str | None = None
    base_url: str
    key: str | None = None
    is_default: bool = False


class AIModelConfigResponse(BaseModel):
    key: str
    display_name: str
    provider_note: str | None = None
    model_id: str
    base_url: str
    has_api_key: bool
    masked_api_key: str | None = None
    is_active: bool
    is_builtin: bool = False


class ProviderConfigResponse(BaseModel):
    provider_key: str
    display_name: str
    base_url: str
    priority: int
    is_active: bool


class MarketDataSourceOption(BaseModel):
    key: str
    label: str
    description: str
    is_available: bool
    is_default: bool = False


class MarketDataSourceConfig(BaseModel):
    """分市场数据源配置"""
    a_share: str = "YFINANCE"  # A 股默认 YFINANCE
    hk_share: str = "YFINANCE"  # 港股默认 YFINANCE
    us_share: str = "YFINANCE"  # 美股默认 YFINANCE


class DataSourceSettingsResponse(BaseModel):
    """数据源设置响应"""
    config: MarketDataSourceConfig
    available_sources: list[MarketDataSourceOption]


class DataSourceSettingsUpdate(BaseModel):
    """数据源设置更新"""
    a_share: str | None = None
    hk_share: str | None = None
    us_share: str | None = None


class UserSettingsUpdate(BaseModel):
    api_key_deepseek: str | None = None
    api_key_siliconflow: str | None = None
    api_configs: dict[str, ApiConfig] | None = None
    provider_credentials: dict[str, UserProviderCredentialInput] | None = None
    fallback_enabled: bool | None = None
    preferred_data_source: str | None = None
    preferred_ai_model: str | None = None
    timezone: str | None = None
    theme: str | None = None
    feishu_webhook_url: str | None = None
    notifications_enabled: bool | None = None
    enable_price_alerts: bool | None = None
    enable_hourly_summary: bool | None = None
    enable_daily_report: bool | None = None
    enable_macro_alerts: bool | None = None


class UserProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    email: str
    membership_tier: str
    has_deepseek_key: bool
    has_siliconflow_key: bool
    api_configs: dict[str, ApiConfig] | None = None
    provider_credentials: dict[str, UserProviderCredentialResponse] | None = None
    fallback_enabled: bool = True
    preferred_data_source: str = "AKSHARE"
    preferred_ai_model: str = settings.DEFAULT_AI_MODEL
    timezone: str = "Asia/Shanghai"
    theme: str = "dark"
    feishu_webhook_url: str | None = None
    notifications_enabled: bool = True
    enable_price_alerts: bool = True
    enable_hourly_summary: bool = True
    enable_daily_report: bool = True
    enable_macro_alerts: bool = True


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class TestConnectionRequest(BaseModel):
    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    model_id: str | None = None
    provider_note: str | None = None


class TestConnectionResponse(BaseModel):
    status: Literal["success", "error"]
    message: str


class TavilyTestRequest(BaseModel):
    api_key: str | None = None
