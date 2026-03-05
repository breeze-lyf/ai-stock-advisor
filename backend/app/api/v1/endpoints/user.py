from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.user_settings import UserSettingsUpdate, UserProfile, PasswordChange
from app.core import security

router = APIRouter()

@router.get("/me", response_model=UserProfile)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "membership_tier": current_user.membership_tier,
        "has_gemini_key": bool(current_user.api_key_gemini),
        "has_deepseek_key": bool(current_user.api_key_deepseek),
        "has_siliconflow_key": bool(current_user.api_key_siliconflow),
        "preferred_data_source": current_user.preferred_data_source or "ALPHA_VANTAGE",
        "preferred_ai_model": current_user.preferred_ai_model or "gemini-1.5-flash",
        "timezone": current_user.timezone or "Asia/Shanghai",
        "theme": current_user.theme or "light",
        "feishu_webhook_url": current_user.feishu_webhook_url,
        "enable_price_alerts": current_user.enable_price_alerts,
        "enable_hourly_summary": current_user.enable_hourly_summary,
        "enable_daily_report": current_user.enable_daily_report,
        "enable_macro_alerts": current_user.enable_macro_alerts
    }

@router.put("/password")
async def change_password(
    data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify old password
    if not security.verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect old password")
    
    # Update to new password
    current_user.hashed_password = security.get_password_hash(data.new_password)
    
    await db.commit()
    return {"status": "success", "message": "Password updated successfully"}

@router.put("/settings", response_model=UserProfile)
async def update_user_settings(
    settings: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if settings.api_key_gemini is not None:
        current_user.api_key_gemini = security.encrypt_api_key(settings.api_key_gemini)
    
    if settings.api_key_deepseek is not None:
        current_user.api_key_deepseek = security.encrypt_api_key(settings.api_key_deepseek)

    if settings.api_key_siliconflow is not None:
        current_user.api_key_siliconflow = security.encrypt_api_key(settings.api_key_siliconflow)

    if settings.preferred_data_source is not None:
        current_user.preferred_data_source = settings.preferred_data_source

    if settings.preferred_ai_model is not None:
        current_user.preferred_ai_model = settings.preferred_ai_model
    
    if settings.timezone is not None:
        current_user.timezone = settings.timezone

    if settings.theme is not None:
        current_user.theme = settings.theme

    if settings.feishu_webhook_url is not None:
        current_user.feishu_webhook_url = settings.feishu_webhook_url
    
    if settings.enable_price_alerts is not None:
        current_user.enable_price_alerts = settings.enable_price_alerts

    if settings.enable_hourly_summary is not None:
        current_user.enable_hourly_summary = settings.enable_hourly_summary

    if settings.enable_daily_report is not None:
        current_user.enable_daily_report = settings.enable_daily_report

    if settings.enable_macro_alerts is not None:
        current_user.enable_macro_alerts = settings.enable_macro_alerts
        
    await db.commit()
    await db.refresh(current_user)
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "membership_tier": current_user.membership_tier,
        "has_gemini_key": bool(current_user.api_key_gemini),
        "has_deepseek_key": bool(current_user.api_key_deepseek),
        "has_siliconflow_key": bool(current_user.api_key_siliconflow),
        "preferred_data_source": current_user.preferred_data_source or "ALPHA_VANTAGE",
        "preferred_ai_model": current_user.preferred_ai_model or "gemini-1.5-flash",
        "timezone": current_user.timezone or "Asia/Shanghai",
        "theme": current_user.theme or "light",
        "feishu_webhook_url": current_user.feishu_webhook_url,
        "enable_price_alerts": current_user.enable_price_alerts,
        "enable_hourly_summary": current_user.enable_hourly_summary,
        "enable_daily_report": current_user.enable_daily_report,
        "enable_macro_alerts": current_user.enable_macro_alerts
    }
