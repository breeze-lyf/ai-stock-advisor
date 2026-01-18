from pydantic import BaseModel
from typing import Optional

class UserSettingsUpdate(BaseModel):
    api_key_gemini: Optional[str] = None
    api_key_deepseek: Optional[str] = None
    preferred_data_source: Optional[str] = None

class UserProfile(BaseModel):
    id: str
    email: str
    membership_tier: str
    has_gemini_key: bool
    has_deepseek_key: bool
    preferred_data_source: str
