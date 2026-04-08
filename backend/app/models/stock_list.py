"""
多股票列表模型
支持用户创建多个自定义股票列表
"""
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from datetime import datetime
from app.core.database import Base


class StockList(Base):
    """
    股票列表主表
    用户可以创建多个股票列表，如"关注列表"、"长线持仓"、"短线观察"等
    """
    __tablename__ = "stock_lists"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否公开
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)

    # 关联
    items = relationship(
        "StockListItem",
        back_populates="list",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    user = relationship("User", back_populates="stock_lists")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_list_name"),
    )


class StockListItem(Base):
    """
    股票列表项
    """
    __tablename__ = "stock_list_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    list_id: Mapped[str] = mapped_column(
        ForeignKey("stock_lists.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 备注
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关联
    list = relationship("StockList", back_populates="items")

    __table_args__ = (
        UniqueConstraint("list_id", "ticker", name="uq_list_ticker"),
    )
