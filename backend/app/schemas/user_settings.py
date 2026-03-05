from pydantic import BaseModel
from typing import Optional

class UserSettingsUpdate(BaseModel):
    api_key_gemini: Optional[str] = None
    api_key_deepseek: Optional[str] = None
    api_key_siliconflow: Optional[str] = None
    preferred_data_source: Optional[str] = None
    preferred_ai_model: Optional[str] = None
    timezone: Optional[str] = None
    theme: Optional[str] = None
    feishu_webhook_url: Optional[str] = None
    enable_price_alerts: Optional[bool] = None
    enable_hourly_summary: Optional[bool] = None
    enable_daily_report: Optional[bool] = None
    enable_macro_alerts: Optional[bool] = None

class UserProfile(BaseModel):
    id: str
    email: str
    membership_tier: str
    has_gemini_key: bool
    has_deepseek_key: bool
    has_siliconflow_key: bool
    preferred_data_source: str
    preferred_ai_model: str
    timezone: str
    theme: str
    feishu_webhook_url: Optional[str]
    enable_price_alerts: bool
    enable_hourly_summary: bool
    enable_daily_report: bool
    enable_macro_alerts: bool

class PasswordChange(BaseModel):
    old_password: str
    new_password: str
