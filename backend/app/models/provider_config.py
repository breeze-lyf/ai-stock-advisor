"""
供应商配置模型 (Provider Config Model)

管理 AI 服务供应商的注册信息，支持动态 URL 切换和故障转移优先级排序。
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from datetime import datetime
import uuid
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

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # 供应商唯一标识符 (Unique provider identifier)
    provider_key = Column(String, unique=True, index=True, nullable=False)
    # 显示名称 (Human-readable display name)
    display_name = Column(String, nullable=False)
    # API 基地址，支持动态修改（如切换到自建代理时只需改这一个字段）
    base_url = Column(String, nullable=False)
    # 对应 .env 中的 API Key 环境变量名
    api_key_env = Column(String, nullable=False)
    # 故障转移优先级：数字越小越优先被选中
    priority = Column(Integer, default=10)
    # 是否启用：关闭后该供应商不参与故障转移
    is_active = Column(Boolean, default=True)
    # 单个供应商的最大重试次数
    max_retries = Column(Integer, default=3)
    # 请求超时（秒），推理模型建议 300s
    timeout_seconds = Column(Integer, default=300)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ProviderConfig(key='{self.provider_key}', url='{self.base_url}', priority={self.priority})>"
