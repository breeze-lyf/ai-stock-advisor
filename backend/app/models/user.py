# 用户模型定义
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from datetime import datetime
from app.core.database import Base
from app.core.config import settings
import enum

# 定义用户特权等级 (用枚举确保数据一致性)
class MembershipTier(str, enum.Enum):
    FREE = "FREE" # 免费用户
    PRO = "PRO"   # 专业版用户

# 数据源选项 (用户偏好设置)
class MarketDataSource(str, enum.Enum):
    AKSHARE = "AKSHARE"
    YFINANCE = "YFINANCE"
    DEFAULT = "DEFAULT"  # 使用系统默认逻辑

# AI 模型选项 (用户可以在个人设置中切换默认模型)
class AIModel(str, enum.Enum):
    DEEPSEEK_V3 = "deepseek-v3"
    DEEPSEEK_R1 = "deepseek-r1"
    QWEN_25_72B = "qwen-2.5-72b"
    QWEN_3_VL_THINKING = "qwen-3-vl-thinking"

# 用户核心表格式 (User Model)
# 职责：存储用户的账户信息、权限等级、以及调用 AI 所需的私密密钥。
class User(Base):
    __tablename__ = "users" # 对应数据库中的表名

    # 使用 UUID 作为主键，比自增 ID 更安全，不容易被外部爬虫猜出用户总量。
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Email 设置为索引 (index=True)，因为它是登录时最常用的查询字段，索引能极大加快查询速度。
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    
    # 安全常识：永远不要在数据库存储明文密码！
    # 这里存储的是经过 Argon2 或 Bcrypt 算法加密后的哈希值。
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # 业务逻辑：FREE 用户可能有每日诊断次数限制，PRO 用户则无限制。
    membership_tier: Mapped[str] = mapped_column(String, default=MembershipTier.FREE.value)
    
    # --- 多平台 AI 密钥管理 ---
    api_key_deepseek: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    api_key_siliconflow: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # 偏好设置 - 分市场数据源配置
    data_source_a_share: Mapped[str] = mapped_column(String, default=MarketDataSource.YFINANCE.value)
    data_source_hk_share: Mapped[str] = mapped_column(String, default=MarketDataSource.YFINANCE.value)
    data_source_us_share: Mapped[str] = mapped_column(String, default=MarketDataSource.YFINANCE.value)
    # 向后兼容：保留原有字段用于迁移
    preferred_data_source: Mapped[str] = mapped_column(String, default=MarketDataSource.YFINANCE.value)
    preferred_ai_model: Mapped[str] = mapped_column(String, default=settings.DEFAULT_AI_MODEL)
    timezone: Mapped[str] = mapped_column(String, default="Asia/Shanghai")
    theme: Mapped[str] = mapped_column(String, default="light")
    feishu_webhook_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # --- 增强型 AI 配置 (BYOK & Dispatching) ---
    api_configs: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    fallback_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # --- 通知精细化控制开关 (Notification Switches) ---
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_price_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_hourly_summary: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_daily_report: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_macro_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    portfolio_items = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    simulated_trades = relationship("SimulatedTrade", back_populates="user", cascade="all, delete-orphan")
