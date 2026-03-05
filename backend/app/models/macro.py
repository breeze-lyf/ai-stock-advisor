from sqlalchemy import Column, String, DateTime, Float, JSON, Text, Boolean
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
    
    # 是否为头条/深度报道
    is_headline = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<GlobalNews(time='{self.published_at}', title='{self.title[:20]}...')>"

class GlobalHourlyReport(Base):
    __tablename__ = "global_hourly_reports"

    # 使用时间指纹作为主键，格式如 "2024-03-05-15"
    hour_key = Column(String, primary_key=True)
    
    core_summary = Column(Text, nullable=False)    # 全局宏观综述
    
    # 影响力映射 JSON: { "AAPL": "利好理由", "TSLA": "利空理由", ... }
    # 以及受影响的 Ticker 列表
    impact_map = Column(JSON)
    
    sentiment = Column(String)                     # 整体情绪定调
    news_count = Column(Float)                     # 本小时汇总的消息数量
    
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<GlobalHourlyReport(hour='{self.hour_key}', news={self.news_count})>"
