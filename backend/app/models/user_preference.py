"""
用户偏好设置模型
存储用户在 onboarding 过程中选择的偏好设置
"""
from sqlalchemy import String, Boolean, ForeignKey, Integer
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.core.database import Base
import enum


class InvestmentProfile(str, enum.Enum):
    """投资偏好"""
    CONSERVATIVE = "CONSERVATIVE"  # 保守型
    BALANCED = "BALANCED"          # 稳健型
    AGGRESSIVE = "AGGRESSIVE"      # 激进型


class MarketPreference(str, enum.Enum):
    """市场偏好"""
    A_SHARE = "A_SHARE"            # A 股
    HK_SHARE = "HK_SHARE"          # 港股
    US_SHARE = "US_SHARE"          # 美股


class NotificationFrequency(str, enum.Enum):
    """通知频率偏好"""
    REALTIME = "REALTIME"          # 实时
    HOURLY = "HOURLY"              # 每小时
    DAILY = "DAILY"                # 每日
    NEVER = "NEVER"                # 免打扰


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False
    )

    # 投资偏好
    investment_profile: Mapped[str] = mapped_column(
        String,
        default=InvestmentProfile.BALANCED.value
    )

    # 市场偏好（逗号分隔的字符串，如 "A_SHARE,US_SHARE"）
    preferred_markets: Mapped[str] = mapped_column(
        String,
        default=MarketPreference.A_SHARE.value
    )

    # 通知频率
    notification_frequency: Mapped[str] = mapped_column(
        String,
        default=NotificationFrequency.REALTIME.value
    )

    # 是否完成 onboarding
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    # 风险承受能力评分（1-10）
    risk_tolerance_score: Mapped[int] = mapped_column(
        Integer,
        default=5
    )

    # 投资经验年数
    investment_experience_years: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    # 目标收益率（年化，百分比）
    target_annual_return: Mapped[int] = mapped_column(
        Integer,
        default=10
    )
