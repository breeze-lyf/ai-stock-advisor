from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text, JSON, Float
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base
import enum

class SentimentScore(str, enum.Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

# AI 诊断报告模型 (Analysis Report Model)
# 职责：永久保存每一次 AI 的诊断结论。
# 它是本系统的核心增值数据，不仅包含原始 Markdown，还通过“结构化字段”驱动前端的可视化组件。

class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    ticker = Column(String, ForeignKey("stocks.ticker"), nullable=False) # 关联的股票
    
    # 原始上下文快照：记录 AI 诊断时那一刻的具体行情，方便溯源 AI 是否看走了眼。
    input_context_snapshot = Column(JSON)
    # AI 返回的完整报告，用于在前端“诊断详情”选项卡中展示。
    ai_response_markdown = Column(Text)
    
    # --- 结构化字段 (由模型输出 JSON 自动解析填充) ---
    # 这些字段非常关键，因为它们决定了前端表格的颜色和“中轴线”的位置。
    
    sentiment_score = Column(String, nullable=True) # 情绪得分 (如: 85)，决定仪表盘指针。
    summary_status = Column(String, nullable=True)  # 模型给出的短评 (如: "空中加油中")。
    risk_level = Column(String, nullable=True)      # 风险等级 (LOW/MEDIUM/HIGH)。
    
    technical_analysis = Column(Text, nullable=True) # 技术面分析详述
    fundamental_news = Column(Text, nullable=True)  # 基本面/消息面详述
    action_advice = Column(Text, nullable=True)     # 具体的文字版操作建议。
    investment_horizon = Column(String, nullable=True) # 投资期限 (短期/中期/长期)。
    confidence_level = Column(Float, nullable=True)    # AI 对该结论的信心指数。
    
    # 交易指令：BUY (买入), HOLD (持有), SELL (卖出)。决定前端卡片的主色调。
    immediate_action = Column(String, nullable=True)  
    
    # --- 价格关键点 (核心点位渲染) ---
    # 下面 these 数值会自动更新到实时行情缓存表，并在图表上画出横线。
    target_price = Column(Float, nullable=True)      # 止盈位
    stop_loss_price = Column(Float, nullable=True)    # 止损位
    
    # 建议建仓区间。
    entry_zone = Column(String, nullable=True)       # 建仓建议区间描述
    entry_price_low = Column(Float, nullable=True)   # 入场下限
    entry_price_high = Column(Float, nullable=True)  # 入场上限
    
    # 盈亏比文本（如 "1:3"），体现该笔交易的性价比。
    rr_ratio = Column(String, nullable=True)        
    
    model_used = Column(String) # 记录是哪位“老师”分析的 (DeepSeek, Gemini 等)。
    
    # 创建时间作为索引，方便用户查看“历史报告”时快速排序。
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    stock = relationship("Stock", back_populates="analysis_reports")
    # user = relationship("User", back_populates="analysis_reports")
