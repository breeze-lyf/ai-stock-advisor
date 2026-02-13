from sqlalchemy import Column, String, Boolean, DateTime
from datetime import datetime
import uuid
from app.core.database import Base

class AIModelConfig(Base):
    __tablename__ = "ai_model_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String, unique=True, index=True, nullable=False)  # e.g., "deepseek-r1"
    provider = Column(String, nullable=False)  # e.g., "siliconflow", "gemini"
    model_id = Column(String, nullable=False)  # e.g., "Pro/deepseek-ai/DeepSeek-R1"
    is_active = Column(Boolean, default=True)
    description = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AIModelConfig(key='{self.key}', provider='{self.provider}', model_id='{self.model_id}')>"
