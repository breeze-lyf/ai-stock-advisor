from sqlalchemy import Column, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base

# 投资组合/自选股关系表
# 记录了哪个用户持有/关注了哪支股票
class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)   # 关联用户
    ticker = Column(String, ForeignKey("stocks.ticker"), nullable=False) # 关联股票代码
    
    # 投资详情
    quantity = Column(Float, nullable=False)      # 持仓数量 (如果是 0 则代表仅自选/观察)
    avg_cost = Column(Float, nullable=False)      # 持仓均价
    target_price = Column(Float, nullable=True)   # 目标价 (预留)
    stop_loss_price = Column(Float, nullable=True) # 止损价 (预留)
    
    created_at = Column(DateTime, default=datetime.utcnow) # 创建时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) # 更新时间

    # 约束条件：同一个用户对同一个 Symbol 只能有一条记录
    __table_args__ = (
        UniqueConstraint('user_id', 'ticker', name='unique_user_stock'),
    )
    
    # 后续可以根据需要添加 relationship
    # user = relationship("User", back_populates="portfolio")
