"""
用户偏好设置 API
"""
from typing import Optional
import enum
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.user_preference import UserPreference, InvestmentProfile, MarketPreference, NotificationFrequency
from sqlalchemy.future import select
from sqlalchemy.sql import func

router = APIRouter()


class InvestmentProfileEnum(str, enum.Enum):
    CONSERVATIVE = "CONSERVATIVE"
    BALANCED = "BALANCED"
    AGGRESSIVE = "AGGRESSIVE"


class MarketPreferenceEnum(str, enum.Enum):
    A_SHARE = "A_SHARE"
    HK_SHARE = "HK_SHARE"
    US_SHARE = "US_SHARE"


class NotificationFrequencyEnum(str, enum.Enum):
    REALTIME = "REALTIME"
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    NEVER = "NEVER"


class OnboardingRequest(BaseModel):
    """Onboarding 请求"""
    investment_profile: InvestmentProfileEnum
    preferred_markets: list[MarketPreferenceEnum] = Field(
        ...,
        min_length=1,
        description="至少选择一个市场"
    )
    notification_frequency: NotificationFrequencyEnum
    risk_tolerance_score: int = Field(
        ...,
        ge=1,
        le=10,
        description="风险承受能力评分 (1-10)"
    )
    investment_experience_years: int = Field(
        ...,
        ge=0,
        le=50,
        description="投资经验年数"
    )
    target_annual_return: int = Field(
        ...,
        ge=0,
        le=200,
        description="目标年化收益率 (%)"
    )


class OnboardingResponse(BaseModel):
    """Onboarding 响应"""
    success: bool
    message: str
    onboarding_completed: bool


class UserPreferenceResponse(BaseModel):
    """用户偏好响应"""
    investment_profile: str
    preferred_markets: list[str]
    notification_frequency: str
    onboarding_completed: bool
    risk_tolerance_score: int
    investment_experience_years: int
    target_annual_return: int

    class Config:
        from_attributes = True


@router.get("/preferences", response_model=UserPreferenceResponse)
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户偏好设置"""
    stmt = select(UserPreference).where(UserPreference.user_id == current_user.id)
    result = await db.execute(stmt)
    preference = result.scalar_one_or_none()

    if not preference:
        # 返回默认值
        return UserPreferenceResponse(
            investment_profile=InvestmentProfile.BALANCED.value,
            preferred_markets=[MarketPreference.A_SHARE.value],
            notification_frequency=NotificationFrequency.REALTIME.value,
            onboarding_completed=False,
            risk_tolerance_score=5,
            investment_experience_years=0,
            target_annual_return=10,
        )

    return UserPreferenceResponse(
        investment_profile=preference.investment_profile,
        preferred_markets=preference.preferred_markets.split(",") if preference.preferred_markets else [],
        notification_frequency=preference.notification_frequency,
        onboarding_completed=preference.onboarding_completed,
        risk_tolerance_score=preference.risk_tolerance_score,
        investment_experience_years=preference.investment_experience_years,
        target_annual_return=preference.target_annual_return,
    )


@router.post("/onboarding", response_model=OnboardingResponse)
async def complete_onboarding(
    request: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """完成新用户引导流程"""
    # 检查是否已完成 onboarding
    stmt = select(UserPreference).where(UserPreference.user_id == current_user.id)
    result = await db.execute(stmt)
    existing_preference = result.scalar_one_or_none()

    if existing_preference and existing_preference.onboarding_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding already completed"
        )

    # 转换市场列表为逗号分隔的字符串
    markets_str = ",".join([m.value for m in request.preferred_markets])

    if existing_preference:
        # 更新现有偏好
        existing_preference.investment_profile = request.investment_profile.value
        existing_preference.preferred_markets = markets_str
        existing_preference.notification_frequency = request.notification_frequency.value
        existing_preference.risk_tolerance_score = request.risk_tolerance_score
        existing_preference.investment_experience_years = request.investment_experience_years
        existing_preference.target_annual_return = request.target_annual_return
        existing_preference.onboarding_completed = True
    else:
        # 创建新偏好
        preference = UserPreference(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            investment_profile=request.investment_profile.value,
            preferred_markets=markets_str,
            notification_frequency=request.notification_frequency.value,
            risk_tolerance_score=request.risk_tolerance_score,
            investment_experience_years=request.investment_experience_years,
            target_annual_return=request.target_annual_return,
            onboarding_completed=True,
        )
        db.add(preference)

    await db.commit()

    return OnboardingResponse(
        success=True,
        message="Onboarding completed successfully",
        onboarding_completed=True,
    )


@router.patch("/preferences", response_model=UserPreferenceResponse)
async def update_user_preferences(
    investment_profile: Optional[InvestmentProfileEnum] = Query(None),
    preferred_markets: Optional[list[MarketPreferenceEnum]] = Query(None),
    notification_frequency: Optional[NotificationFrequencyEnum] = Query(None),
    risk_tolerance_score: Optional[int] = Query(None, ge=1, le=10),
    investment_experience_years: Optional[int] = Query(None, ge=0, le=50),
    target_annual_return: Optional[int] = Query(None, ge=0, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """部分更新用户偏好"""
    stmt = select(UserPreference).where(UserPreference.user_id == current_user.id)
    result = await db.execute(stmt)
    preference = result.scalar_one_or_none()

    if not preference:
        # 创建新的偏好
        markets_str = ",".join([m.value for m in preferred_markets]) if preferred_markets else MarketPreference.A_SHARE.value
        preference = UserPreference(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            investment_profile=investment_profile.value if investment_profile else InvestmentProfile.BALANCED.value,
            preferred_markets=markets_str,
            notification_frequency=notification_frequency.value if notification_frequency else NotificationFrequency.REALTIME.value,
            risk_tolerance_score=risk_tolerance_score if risk_tolerance_score is not None else 5,
            investment_experience_years=investment_experience_years if investment_experience_years is not None else 0,
            target_annual_return=target_annual_return if target_annual_return is not None else 10,
        )
        db.add(preference)
    else:
        # 更新现有偏好
        if investment_profile:
            preference.investment_profile = investment_profile.value
        if preferred_markets:
            preference.preferred_markets = ",".join([m.value for m in preferred_markets])
        if notification_frequency:
            preference.notification_frequency = notification_frequency.value
        if risk_tolerance_score is not None:
            preference.risk_tolerance_score = risk_tolerance_score
        if investment_experience_years is not None:
            preference.investment_experience_years = investment_experience_years
        if target_annual_return is not None:
            preference.target_annual_return = target_annual_return

    await db.commit()
    await db.refresh(preference)

    return UserPreferenceResponse(
        investment_profile=preference.investment_profile,
        preferred_markets=preference.preferred_markets.split(",") if preference.preferred_markets else [],
        notification_frequency=preference.notification_frequency,
        onboarding_completed=preference.onboarding_completed,
        risk_tolerance_score=preference.risk_tolerance_score,
        investment_experience_years=preference.investment_experience_years,
        target_annual_return=preference.target_annual_return,
    )
