from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.models.notification import NotificationLog
from pydantic import BaseModel, ConfigDict
from datetime import datetime

router = APIRouter()

from app.core.database import get_db

class NotificationHistorySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    title: str
    content: str
    card_payload: dict
    created_at: datetime

@router.get("/history", response_model=List[NotificationHistorySchema])
async def get_notification_history(
    limit: int = Query(20, gt=0, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    获取通知历史记录流
    """
    stmt = select(NotificationLog).order_by(NotificationLog.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()
