from sqlalchemy import Column, String, DateTime, JSON, Text
import uuid
from datetime import datetime, timezone
from app.core.database import Base

class NotificationLog(Base):
    """
    通知历史记录表 (Smart Alert Stream)
    职责：持久化飞书机器人推送过的信息，用于前端展示“提醒流”。
    """
    __tablename__ = "notification_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True, nullable=True) # 归属用户 ID
    ticker = Column(String, index=True, nullable=True) # 关联的股票代码 (用于去重)
    type = Column(String, index=True) # 提醒类型: MACRO_ALERT, PRICE_ALERT, DAILY_REPORT, INDICATOR_ALERT
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True) # 核心纯文本内容（用于搜索/展示详情）
    card_payload = Column(JSON, nullable=True) # 完整的飞书卡片 JSON 载体
    status = Column(String, default="SUCCESS") # 发送状态
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
