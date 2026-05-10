from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.models.notification import NotificationLog
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

from app.core.database import get_db

class NotificationHistorySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    ticker: str | None = None
    target_id: str | None = None
    semantic_key: str | None = None
    priority: str | None = None
    title: str
    content: str
    card_payload: dict | None
    created_at: datetime

@router.get("/history", response_model=List[NotificationHistorySchema])
async def get_notification_history(
    limit: int = Query(20, gt=0, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取通知历史记录流
    """
    stmt = (
        select(NotificationLog)
        .where(NotificationLog.user_id == current_user.id)
        .order_by(NotificationLog.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
