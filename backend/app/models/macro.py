from sqlalchemy import Column, String, DateTime, Float, JSON, Text
from datetime import datetime
import uuid
from app.core.database import Base

class MacroTopic(Base):
    __tablename__ = "macro_topics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)        # 热点标题
    summary = Column(Text, nullable=True)         # AI 总结背景
    heat_score = Column(Float, default=50.0)      # 热度指数 (0-100)
    
    # 影响力分析结构化数据
    impact_analysis = Column(JSON)
    
    source_links = Column(JSON)                   # 来源链接列表
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<MacroTopic(title='{self.title}', heat={self.heat_score})>"

class GlobalNews(Base):
    __tablename__ = "global_news"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    published_at = Column(String, nullable=False)  # 财联社发布的原始时间字符串
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    
    # 用于排重的唯一指纹 (通常是 content + published_at 的 MD5)
    fingerprint = Column(String, unique=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<GlobalNews(time='{self.published_at}', title='{self.title[:20]}...')>"
