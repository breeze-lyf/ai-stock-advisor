"""
供应商配置模型 (Provider Config Model)

管理 AI 服务供应商的注册信息，支持动态 URL 切换和故障转移优先级排序。
"""
from datetime import datetime
import uuid
from sqlalchemy import String, Boolean, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ProviderConfig(Base):
    """
    AI 供应商注册表：
    - provider_key: 供应商唯一标识 (如 "siliconflow", "gemini", "deepseek-direct")
    - base_url: API 基地址 (如 "https://api.siliconflow.cn/v1")
    - api_key_env: 对应 .env 中的环境变量名 (如 "SILICONFLOW_API_KEY")
    - priority: 故障转移优先级，数字越小优先级越高
    - is_active: 是否启用
    - max_retries: 单个供应商的最大重试次数
    - timeout_seconds: 请求超时时间
    """
    __tablename__ = "provider_configs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_key: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    base_url: Mapped[str] = mapped_column(String, nullable=False)
    api_key_env: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=10)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ProviderConfig(key='{self.provider_key}', url='{self.base_url}', priority={self.priority})>"
