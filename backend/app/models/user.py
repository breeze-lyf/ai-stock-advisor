from sqlalchemy import Column, String, Boolean, DateTime, Enum
import uuid
from datetime import datetime
from app.core.database import Base
import enum

class MembershipTier(str, enum.Enum):
    FREE = "FREE"
    PRO = "PRO"

class MarketDataSource(str, enum.Enum):
    ALPHA_VANTAGE = "ALPHA_VANTAGE"
    YFINANCE = "YFINANCE"

class AIModel(str, enum.Enum):
    GEMINI_15_FLASH = "gemini-1.5-flash"
    DEEPSEEK_V3 = "deepseek-v3"
    DEEPSEEK_R1 = "deepseek-r1"
    QWEN_25_72B = "qwen-2.5-72b"
    QWEN_3_VL_THINKING = "qwen-3-vl-thinking"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    membership_tier = Column(String, default=MembershipTier.FREE.value)
    
    # Encrypted API Keys
    api_key_gemini = Column(String, nullable=True)
    api_key_deepseek = Column(String, nullable=True) # Standard DeepSeek API
    api_key_siliconflow = Column(String, nullable=True) # SiliconFlow API
    
    preferred_data_source = Column(String, default=MarketDataSource.ALPHA_VANTAGE.value)
    preferred_ai_model = Column(String, default=AIModel.GEMINI_15_FLASH.value)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
