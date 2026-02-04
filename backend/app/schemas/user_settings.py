from pydantic import BaseModel
from typing import Optional

class UserSettingsUpdate(BaseModel):
    api_key_gemini: Optional[str] = None
    api_key_deepseek: Optional[str] = None
    api_key_siliconflow: Optional[str] = None
    preferred_data_source: Optional[str] = None
    preferred_ai_model: Optional[str] = None

class UserProfile(BaseModel):
    id: str
    email: str
    membership_tier: str
    has_gemini_key: bool
    has_deepseek_key: bool
    has_siliconflow_key: bool
    preferred_data_source: str
    preferred_ai_model: str
