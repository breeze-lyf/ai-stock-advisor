from pydantic import BaseModel
from typing import Optional

class AIModelRuntimeConfig(BaseModel):
    """用于运行时传递的 AI 模型配置（解耦 SQLAlchemy ORM）"""
    key: str
    provider: str
    model_id: str
    description: Optional[str] = None

class ProviderRuntimeConfig(BaseModel):
    """用于运行时传递的供应商配置"""
    provider_key: str
    base_url: str
    timeout_seconds: int = 300
