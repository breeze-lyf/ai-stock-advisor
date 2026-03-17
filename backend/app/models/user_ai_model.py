from datetime import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, UniqueConstraint

from app.core.database import Base


class UserAIModel(Base):
    __tablename__ = "user_ai_models"
    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_user_ai_models_user_key"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    provider_note = Column(String, nullable=True)
    model_id = Column(String, nullable=False)
    encrypted_api_key = Column(String, nullable=True)
    base_url = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
