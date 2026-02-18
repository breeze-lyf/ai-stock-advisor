# 用户模型定义
from sqlalchemy import Column, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base
import enum

# 定义用户特权等级 (用枚举确保数据一致性)
class MembershipTier(str, enum.Enum):
    FREE = "FREE" # 免费用户
    PRO = "PRO"   # 专业版用户

# 数据源选项 (用户偏好设置)
class MarketDataSource(str, enum.Enum):
    ALPHA_VANTAGE = "ALPHA_VANTAGE"
    YFINANCE = "YFINANCE"

# AI 模型选项 (用户可以在个人设置中切换默认模型)
class AIModel(str, enum.Enum):
    GEMINI_15_FLASH = "gemini-1.5-flash"
    DEEPSEEK_V3 = "deepseek-v3"
    DEEPSEEK_R1 = "deepseek-r1"
    QWEN_25_72B = "qwen-2.5-72b"
    QWEN_3_VL_THINKING = "qwen-3-vl-thinking"

# 用户核心表格式 (User Model)
# 职责：存储用户的账户信息、权限等级、以及调用 AI 所需的私密密钥。
class User(Base):
    __tablename__ = "users" # 对应数据库中的表名

    # 使用 UUID 作为主键，比自增 ID 更安全，不容易被外部爬虫猜出用户总量。
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Email 设置为索引 (index=True)，因为它是登录时最常用的查询字段，索引能极大加快查询速度。
    email = Column(String, unique=True, index=True, nullable=False) 
    
    # 安全常识：永远不要在数据库存储明文密码！
    # 这里存储的是经过 Argon2 或 Bcrypt 算法加密后的哈希值。
    hashed_password = Column(String, nullable=False)               
    
    is_active = Column(Boolean, default=True)                      # 用于账号风控（如禁用违规账号）
    
    # 业务逻辑：FREE 用户可能有每日诊断次数限制，PRO 用户则无限制。
    membership_tier = Column(String, default=MembershipTier.FREE.value) 
    
    # --- 多平台 AI 密钥管理 ---
    # 我们支持多厂家模型，用户可以填入自己的 Key。
    api_key_gemini = Column(String, nullable=True)     # Google Gemini
    api_key_deepseek = Column(String, nullable=True)   # DeepSeek 官方 (常断连，作为备选)
    
    # 强烈推荐使用的国产聚合平台，直连丝滑，支持 DeepSeek 和 Qwen。
    api_key_siliconflow = Column(String, nullable=True) 
    
    # 偏好设置：用户可以自定义使用哪里的行情，以及默认喜欢哪个分析师(AI模型)。
    preferred_data_source = Column(String, default=MarketDataSource.ALPHA_VANTAGE.value) 
    preferred_ai_model = Column(String, default=AIModel.QWEN_3_VL_THINKING.value)        
    
    created_at = Column(DateTime, default=datetime.utcnow) # 记录生日(注册时间)
    last_login = Column(DateTime, nullable=True)           # 活跃度追踪
    
    # Relationships
    portfolio_items = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
