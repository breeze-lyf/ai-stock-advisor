"""
用户投资偏好模型
存储用户在 onboarding 流程中设置的投资偏好
"""
from typing import Optional, Dict, Any
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Text, Numeric, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime
from app.core.database import Base


class UserInvestmentProfile(Base):
    """
    用户投资画像
    记录用户的投资偏好、风险承受能力、关注市场等
    """
    __tablename__ = "user_investment_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False
    )

    # 风险偏好
    risk_tolerance: Mapped[str] = mapped_column(String(20), default="MODERATE")  # CONSERVATIVE/MODERATE/AGGRESSIVE
    risk_tolerance_score: Mapped[int] = mapped_column(Integer, default=5)  # 1-10 分

    # 投资经验
    investment_experience: Mapped[str] = mapped_column(String(50), default="BEGINNER")  # BEGINNER/INTERMEDIATE/ADVANCED
    investment_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 关注市场
    preferred_markets: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 逗号分隔：US,HK,CN
    default_market: Mapped[Optional[str]] = mapped_column(String(10), default="US")  # US/HK/CN

    # 投资风格
    investment_style: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # VALUE/GROWTH/MOMENTUM/INCOME
    investment_horizon: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # SHORT/MEDIUM/LONG

    # 持仓规模
    portfolio_size: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # SMALL/MEDIUM/LARGE
    target_annual_return: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)  # 目标年化收益率

    # 通知偏好
    notification_preferences: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # EMAIL/PUSH/SMS

    # Onboarding 状态
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)


class UserDashboardConfig(Base):
    """
    用户仪表盘配置
    允许用户自定义首页显示的模块和布局
    """
    __tablename__ = "user_dashboard_configs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False
    )

    # 布局配置（JSON 存储）
    # 示例：{"layout": "grid", "modules": [{"id": "portfolio", "order": 1, "visible": true}, ...]}
    layout_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)

    # 主题偏好
    theme: Mapped[str] = mapped_column(String(20), default="light")  # light/dark/auto
    color_scheme: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # blue/green/purple

    # 显示偏好
    show_portfolio_summary: Mapped[bool] = mapped_column(Boolean, default=True)
    show_market_overview: Mapped[bool] = mapped_column(Boolean, default=True)
    show_ai_signals: Mapped[bool] = mapped_column(Boolean, default=True)
    show_news_feed: Mapped[bool] = mapped_column(Boolean, default=True)
    show_watchlist: Mapped[bool] = mapped_column(Boolean, default=True)

    # 默认视图
    default_view: Mapped[str] = mapped_column(String(20), default="dashboard")  # dashboard/portfolio/screener

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)


class UserEducationProgress(Base):
    """
    用户学习进度（投资者教育）
    记录用户完成的课程和测验
    """
    __tablename__ = "user_education_progress"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    course_id: Mapped[str] = mapped_column(
        ForeignKey("investment_courses.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    lesson_id: Mapped[str] = mapped_column(
        ForeignKey("investment_lessons.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    # 进度状态
    status: Mapped[str] = mapped_column(String(20), default="NOT_STARTED")  # NOT_STARTED/IN_PROGRESS/COMPLETED
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)  # 0-100

    # 测验结果
    quiz_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-100
    quiz_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    quiz_attempts: Mapped[int] = mapped_column(Integer, default=0)

    # 学习时间
    time_spent_minutes: Mapped[int] = mapped_column(Integer, default=0)

    # 元数据
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)


class InvestmentCourse(Base):
    """
    投资课程
    """
    __tablename__ = "investment_courses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # BEGINNER/INTERMEDIATE/ADVANCED
    difficulty: Mapped[str] = mapped_column(String(20), default="BEGINNER")  # BEGINNER/INTERMEDIATE/ADVANCED

    # 课程信息
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    total_lessons: Mapped[int] = mapped_column(Integer, default=0)
    total_points: Mapped[int] = mapped_column(Integer, default=0)  # 完成课程可获得的积分

    # 排序和可见性
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)


class InvestmentLesson(Base):
    """
    投资课程章节
    """
    __tablename__ = "investment_lessons"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id: Mapped[str] = mapped_column(
        ForeignKey("investment_courses.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Markdown 格式内容
    video_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # 章节信息
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, default=10)
    points: Mapped[int] = mapped_column(Integer, default=10)  # 完成本节可获得的积分

    # 测验配置
    has_quiz: Mapped[bool] = mapped_column(Boolean, default=True)
    quiz_passing_score: Mapped[int] = mapped_column(Integer, default=70)  # 及格线 70%
    quiz_questions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)  # JSON 存储问题

    # 元数据
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)
