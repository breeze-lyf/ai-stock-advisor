from datetime import datetime
import uuid
from typing import Optional

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, DateTime

from app.core.database import Base


class UserAIModel(Base):
    __tablename__ = "user_ai_models"
    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_user_ai_models_user_key"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    provider_note: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    model_id: Mapped[str] = mapped_column(String, nullable=False)
    encrypted_api_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    base_url: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
