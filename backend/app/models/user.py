from sqlalchemy import Column, String, Boolean, DateTime, Enum
import uuid
from datetime import datetime
from app.core.database import Base
import enum

class MembershipTier(str, enum.Enum):
    FREE = "FREE"
    PRO = "PRO"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    membership_tier = Column(Enum(MembershipTier), default=MembershipTier.FREE)
    
    # Encrypted API Keys (Placeholder for now, storing raw/base64 in MVP if needed, but schema says encrypted)
    api_key_gemini = Column(String, nullable=True)
    api_key_deepseek = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
