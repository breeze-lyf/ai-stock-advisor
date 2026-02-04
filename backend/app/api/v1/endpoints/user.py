from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.user_settings import UserSettingsUpdate, UserProfile
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
        "preferred_ai_model": current_user.preferred_ai_model or "gemini-1.5-flash"
    }

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
        "preferred_ai_model": current_user.preferred_ai_model or "gemini-1.5-flash"
    }
