from __future__ import annotations
import json
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.config import settings as core_settings
from app.core.database import get_db
from app.infrastructure.db.repositories.ai_model_repository import AIModelRepository
from app.infrastructure.db.repositories.provider_config_repository import ProviderConfigRepository
from app.infrastructure.db.repositories.user_ai_model_repository import UserAIModelRepository
from app.infrastructure.db.repositories.user_repository import UserRepository
from app.infrastructure.db.repositories.user_provider_credential_repository import UserProviderCredentialRepository
from app.models.user import User
from app.models.user_ai_model import UserAIModel
from app.schemas.user_settings import (
    AIModelConfigCreate,
    AIModelConfigResponse,
    DataSourceSettingsResponse,
    DataSourceSettingsUpdate,
    FeishuWebhookTestRequest,
    MarketDataSourceConfig,
    MarketDataSourceOption,
    PasswordChange,
    ProviderConfigResponse,
    TavilyTestRequest,
    TestConnectionRequest,
    TestConnectionResponse,
    UserProviderCredentialResponse,
    UserProfile,
    UserSettingsUpdate,
)
from app.core import security

router = APIRouter()
PUBLIC_SYSTEM_MODEL_KEYS = {"qwen3.5-plus"}
SUPPORTED_DATA_SOURCES = {"AKSHARE", "YFINANCE"}


def get_data_source_config() -> DataSourceSettingsResponse:
    """获取数据源配置"""
    return DataSourceSettingsResponse(
        config=MarketDataSourceConfig(
            a_share="YFINANCE",
            hk_share="YFINANCE",
            us_share="YFINANCE",
        ),
        available_sources=get_market_data_source_options()
    )


def build_model_key(display_name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", display_name.strip().lower()).strip("-")
    return normalized or "custom-model"


def mask_secret(secret: str | None) -> str | None:
    if not secret:
        return None
    if len(secret) <= 8:
        return f"{secret[:2]}****"
    return f"{secret[:4]}{'•' * max(4, min(8, len(secret) - 8))}{secret[-4:]}"


def get_market_data_source_options() -> list[MarketDataSourceOption]:
    return [
        MarketDataSourceOption(
            key="AKSHARE",
            label="AkShare",
            description="适合国内服务器环境，优先走东方财富、腾讯、新浪等国内可达数据链路。",
            is_available=True,
            is_default=True,
        ),
        MarketDataSourceOption(
            key="YFINANCE",
            label="Yahoo Finance",
            description="适合海外服务器环境，使用 yfinance 直连 Yahoo Finance 行情与历史数据。",
            is_available=True,
            is_default=False,
        ),
    ]


def normalize_preferred_data_source(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None

    normalized = raw_value.strip().upper()
    if normalized not in SUPPORTED_DATA_SOURCES:
        raise HTTPException(status_code=400, detail="不支持的数据源")

    options = {item.key: item for item in get_market_data_source_options()}
    option = options.get(normalized)
    if option is None or not option.is_available:
        raise HTTPException(status_code=400, detail=f"数据源 {normalized} 当前不可用")

    return normalized


def serialize_user_profile(current_user: User, provider_credentials: dict[str, UserProviderCredentialResponse] | None = None) -> UserProfile:
    api_configs = {}
    if current_user.api_configs:
        try:
            api_configs = json.loads(current_user.api_configs)
        except json.JSONDecodeError:
            api_configs = {}

    provider_credentials = provider_credentials or {}
    has_deepseek = bool(current_user.api_key_deepseek) or provider_credentials.get("deepseek", UserProviderCredentialResponse(has_key=False, is_enabled=True)).has_key
    has_siliconflow = bool(current_user.api_key_siliconflow) or provider_credentials.get("siliconflow", UserProviderCredentialResponse(has_key=False, is_enabled=True)).has_key

    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        membership_tier=current_user.membership_tier,
        has_deepseek_key=has_deepseek,
        has_siliconflow_key=has_siliconflow,
        api_configs=api_configs,
        provider_credentials=provider_credentials,
        fallback_enabled=current_user.fallback_enabled if current_user.fallback_enabled is not None else True,
        preferred_data_source=current_user.preferred_data_source or "YFINANCE",
        preferred_ai_model=current_user.preferred_ai_model or core_settings.DEFAULT_AI_MODEL,
        timezone=current_user.timezone or "Asia/Shanghai",
        theme=current_user.theme or "light",
        feishu_webhook_url=current_user.feishu_webhook_url,
        notifications_enabled=current_user.notifications_enabled if current_user.notifications_enabled is not None else True,
        enable_price_alerts=current_user.enable_price_alerts if current_user.enable_price_alerts is not None else True,
        enable_hourly_summary=current_user.enable_hourly_summary if current_user.enable_hourly_summary is not None else True,
        enable_daily_report=current_user.enable_daily_report if current_user.enable_daily_report is not None else True,
        enable_macro_alerts=current_user.enable_macro_alerts if current_user.enable_macro_alerts is not None else True,
    )


async def build_provider_credential_map(db: AsyncSession, user_id: str) -> dict[str, UserProviderCredentialResponse]:
    repo = UserProviderCredentialRepository(db)
    credentials = await repo.list_by_user_id(user_id)
    return {
        credential.provider_key: UserProviderCredentialResponse(
            has_key=bool(credential.encrypted_api_key),
            base_url=credential.base_url,
            is_enabled=credential.is_enabled,
        )
        for credential in credentials
    }


@router.get("/me", response_model=UserProfile)
async def read_users_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    provider_credentials = await build_provider_credential_map(db, current_user.id)
    return serialize_user_profile(current_user, provider_credentials)


@router.get("/market-data-sources", response_model=list[MarketDataSourceOption])
async def list_market_data_sources(_: User = Depends(get_current_user)):
    return get_market_data_source_options()

@router.put("/password")
async def change_password(
    data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = UserRepository(db)
    # Verify old password
    if not security.verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect old password")
    
    # Update to new password
    current_user.hashed_password = security.get_password_hash(data.new_password)
    
    await repo.save(current_user)
    return {"status": "success", "message": "Password updated successfully"}

@router.put("/settings", response_model=UserProfile)
async def update_user_settings(
    settings: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = UserRepository(db)
    credential_repo = UserProviderCredentialRepository(db)

    if settings.api_key_deepseek is not None:
        current_user.api_key_deepseek = security.encrypt_api_key(settings.api_key_deepseek)

    if settings.api_key_siliconflow is not None:
        current_user.api_key_siliconflow = security.encrypt_api_key(settings.api_key_siliconflow)

    if settings.api_configs is not None:
        current_user.api_configs = json.dumps(
            {key: value.model_dump() for key, value in settings.api_configs.items()}
        )

    if settings.provider_credentials is not None:
        for provider_key, credential in settings.provider_credentials.items():
            normalized_key = provider_key.strip().lower()
            encrypted_api_key = None
            if credential.api_key is not None:
                encrypted_api_key = security.encrypt_api_key(credential.api_key) if credential.api_key else None

            await credential_repo.upsert(
                user_id=current_user.id,
                provider_key=normalized_key,
                encrypted_api_key=encrypted_api_key,
                base_url=credential.base_url,
                is_enabled=credential.is_enabled,
            )
    
    if settings.fallback_enabled is not None:
        current_user.fallback_enabled = settings.fallback_enabled

    if settings.preferred_data_source is not None:
        normalized_source = normalize_preferred_data_source(settings.preferred_data_source)
        assert normalized_source is not None
        current_user.preferred_data_source = normalized_source

    if settings.preferred_ai_model is not None:
        current_user.preferred_ai_model = settings.preferred_ai_model
    
    if settings.timezone is not None:
        current_user.timezone = settings.timezone

    if settings.theme is not None:
        current_user.theme = settings.theme

    if settings.feishu_webhook_url is not None:
        current_user.feishu_webhook_url = settings.feishu_webhook_url
    
    if settings.notifications_enabled is not None:
        current_user.notifications_enabled = settings.notifications_enabled
    
    if settings.enable_price_alerts is not None:
        current_user.enable_price_alerts = settings.enable_price_alerts

    if settings.enable_hourly_summary is not None:
        current_user.enable_hourly_summary = settings.enable_hourly_summary

    if settings.enable_daily_report is not None:
        current_user.enable_daily_report = settings.enable_daily_report

    if settings.enable_macro_alerts is not None:
        current_user.enable_macro_alerts = settings.enable_macro_alerts

    saved_user = await repo.save(current_user, refresh=False)
    await credential_repo.commit()
    provider_credentials = await build_provider_credential_map(db, current_user.id)
    return serialize_user_profile(saved_user, provider_credentials)

@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_ai_connection(
    request: TestConnectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.services.ai_service import AIService

    import time
    start_all = time.time()

    provider_key = (
        request.provider.strip().lower()
        if request.provider and request.provider.strip()
        else AIService.infer_provider_key(request.base_url, request.provider_note)
    )

    # Resolve Key
    resolve_start = time.time()
    final_api_key = request.api_key
    final_base_url = request.base_url

    if not final_api_key:
        resolved_key, resolved_url = await AIService._resolve_api_key(
            provider_key, current_user, db
        )
        final_api_key = resolved_key
        if not final_base_url:
            final_base_url = resolved_url

        if not final_api_key and request.model_id:
            repo = UserAIModelRepository(db)
            stmt = select(UserAIModel).where(
                UserAIModel.user_id == current_user.id,
                UserAIModel.model_id == request.model_id
            )
            result = await db.execute(stmt)
            saved_model = result.scalars().first()
            if saved_model and saved_model.encrypted_api_key:
                final_api_key = security.decrypt_api_key(saved_model.encrypted_api_key)
                if not final_base_url:
                    final_base_url = saved_model.base_url
    
    print(f"[AI_DEBUG] 凭据解析耗时: {time.time() - resolve_start:.3f}s")

    if not final_api_key:
        return TestConnectionResponse(status="error", message=f"No API Key found")

    # Test Connection
    test_start = time.time()
    success, message = await AIService.test_connection(
        provider_key, final_api_key, final_base_url, db, request.model_id,
    )
    print(f"[AI_DEBUG] 核心测试方法总耗时 (Service端): {time.time() - test_start:.3f}s")
    print(f"[AI_DEBUG] Endpoint 总生命周期: {time.time() - start_all:.3f}s")
    if not success:
        return TestConnectionResponse(status="error", message=message)

    return TestConnectionResponse(status="success", message="Connection successful")


@router.post("/test-tavily", response_model=TestConnectionResponse)
async def test_tavily_connection(
    request: TavilyTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.market_providers.tavily import TavilyProvider

    api_key = request.api_key.strip() if request.api_key and request.api_key.strip() else None
    if not api_key:
        credential_repo = UserProviderCredentialRepository(db)
        credential = await credential_repo.get_by_user_and_provider(current_user.id, "tavily")
        if credential and credential.encrypted_api_key and credential.is_enabled:
            api_key = security.decrypt_api_key(credential.encrypted_api_key)

    if not api_key:
        return TestConnectionResponse(status="error", message="No Tavily API Key found")

    try:
        provider = TavilyProvider(api_key=api_key)
        news = await provider.get_news("AAPL")
        if isinstance(news, list):
            return TestConnectionResponse(status="success", message=f"Tavily connection successful (items={len(news)})")
        return TestConnectionResponse(status="error", message="Tavily returned unexpected response")
    except Exception as exc:
        return TestConnectionResponse(status="error", message=f"Tavily connection failed: {exc}")


@router.post("/test-feishu-webhook", response_model=TestConnectionResponse)
async def test_feishu_webhook(
    request: FeishuWebhookTestRequest,
    current_user: User = Depends(get_current_user),
):
    import httpx

    webhook_url = request.webhook_url.strip() if request.webhook_url and request.webhook_url.strip() else None
    if not webhook_url:
        webhook_url = current_user.feishu_webhook_url

    if not webhook_url:
        return TestConnectionResponse(status="error", message="No Feishu webhook URL configured")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook_url,
                json={
                    "msg_type": "text",
                    "content": {
                        "text": "👋 这是一条测试消息\n\n如果您收到此消息，说明 Webhook 配置正确。"
                    }
                },
            )
            if response.status_code == 200:
                resp_data = response.json()
                if resp_data.get("code") == 0:
                    return TestConnectionResponse(status="success", message="飞书 Webhook 测试成功！")
                return TestConnectionResponse(status="error", message=f"飞书返回错误：{resp_data.get('msg', 'Unknown error')}")
            return TestConnectionResponse(status="error", message=f"HTTP {response.status_code}: {response.text}")
    except httpx.TimeoutException:
        return TestConnectionResponse(status="error", message="请求超时，请检查网络连接")
    except httpx.ConnectError as exc:
        return TestConnectionResponse(status="error", message=f"连接失败：{exc}")
    except Exception as exc:
        return TestConnectionResponse(status="error", message=f"测试失败：{exc}")


@router.get("/ai-models", response_model=list[AIModelConfigResponse])
async def list_ai_models(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_repo = UserAIModelRepository(db)
    provider_repo = ProviderConfigRepository(db)
    builtin_repo = AIModelRepository(db)

    user_models = [
        AIModelConfigResponse(
            key=config.key,
            display_name=config.display_name,
            provider_note=config.provider_note,
            model_id=config.model_id,
            base_url=config.base_url,
            has_api_key=bool(config.encrypted_api_key),
            masked_api_key=mask_secret(security.decrypt_api_key(config.encrypted_api_key)) if config.encrypted_api_key else None,
            is_active=config.is_active,
            is_builtin=False,
        )
        for config in await user_repo.list_active_by_user(current_user.id)
    ]

    provider_map = {provider.provider_key: provider for provider in await provider_repo.list_active()}
    from app.services.ai_service import AIService

    builtin_models = []
    for config in await builtin_repo.list_active():
        if config.key not in PUBLIC_SYSTEM_MODEL_KEYS:
            continue
        provider = provider_map.get(config.provider)
        system_api_key, _ = await AIService._resolve_api_key(config.provider, None, db)
        builtin_models.append(
            AIModelConfigResponse(
                key=config.key,
                display_name=(config.description or config.key).replace("[builtin-public] ", ""),
                provider_note=f"{provider.display_name if provider else config.provider}（系统内置）",
                model_id=config.model_id,
                base_url=provider.base_url if provider else "",
                has_api_key=bool(system_api_key),
                masked_api_key=mask_secret(system_api_key) if system_api_key else None,
                is_active=config.is_active,
                is_builtin=True,
            )
        )

    return builtin_models + user_models


@router.post("/ai-models", response_model=AIModelConfigResponse)
async def upsert_ai_model(
    payload: AIModelConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = UserAIModelRepository(db)
    normalized_key = (payload.key or build_model_key(payload.display_name)).strip().lower()
    try:
        config = await repo.get_by_key(current_user.id, normalized_key)
        if config is None:
            if not payload.api_key or not payload.api_key.strip():
                raise HTTPException(status_code=400, detail="新增模型时必须提供 API Key")
            config = UserAIModel(
                user_id=current_user.id,
                key=normalized_key,
                display_name=payload.display_name.strip(),
                provider_note=payload.provider_note.strip() if payload.provider_note else None,
                model_id=payload.model_id.strip(),
                encrypted_api_key=security.encrypt_api_key(payload.api_key.strip()),
                base_url=payload.base_url.strip(),
                is_active=True,
            )
        else:
            config.display_name = payload.display_name.strip()
            config.provider_note = payload.provider_note.strip() if payload.provider_note else None
            config.model_id = payload.model_id.strip()
            if payload.api_key is not None and payload.api_key.strip():
                config.encrypted_api_key = security.encrypt_api_key(payload.api_key.strip())
            config.base_url = payload.base_url.strip()
            config.is_active = True

        saved = await repo.save(config, refresh=False)
        
        # 如果勾选了设为默认，同步更新用户偏好
        if payload.is_default:
            current_user.preferred_ai_model = saved.key
            # 这里 repo.save(config) 已经 commit 了吗？
            # 实际上 repo.save 内部通常会 commit。
            # 为了保险，我们需要确保 User 对象的修改也被持久化。
            db.add(current_user)
            await db.commit()

        return AIModelConfigResponse(
            key=saved.key,
            display_name=saved.display_name,
            provider_note=saved.provider_note,
            model_id=saved.model_id,
            base_url=saved.base_url,
            has_api_key=bool(saved.encrypted_api_key),
            masked_api_key=mask_secret(security.decrypt_api_key(saved.encrypted_api_key)) if saved.encrypted_api_key else None,
            is_active=saved.is_active,
        )
    except Exception:
        await repo.rollback()
        raise


@router.delete("/ai-models/{model_key}")
async def delete_ai_model(
    model_key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized_key = model_key.strip().lower()
    if normalized_key in PUBLIC_SYSTEM_MODEL_KEYS:
        raise HTTPException(status_code=403, detail="系统内置模型不允许删除")
    repo = UserAIModelRepository(db)
    config = await repo.get_by_key(current_user.id, normalized_key)
    if config is None or not config.is_active:
        raise HTTPException(status_code=404, detail="模型不存在")

    await repo.deactivate(config)

    if current_user.preferred_ai_model == normalized_key:
        current_user.preferred_ai_model = core_settings.DEFAULT_AI_MODEL
        user_repo = UserRepository(db)
        await user_repo.save(current_user)

    return {"status": "success", "message": f"模型 {normalized_key} 已删除"}


@router.get("/providers", response_model=list[ProviderConfigResponse])
async def list_providers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = ProviderConfigRepository(db)
    providers = await repo.list_active()
    return [
        ProviderConfigResponse(
            provider_key=provider.provider_key,
            display_name=provider.display_name,
            base_url=provider.base_url,
            priority=provider.priority,
            is_active=provider.is_active,
        )
        for provider in providers
    ]


@router.get("/data-sources", response_model=DataSourceSettingsResponse)
async def get_data_sources(
    current_user: User = Depends(get_current_user),
):
    """获取数据源配置选项"""
    return DataSourceSettingsResponse(
        config=MarketDataSourceConfig(
            a_share=getattr(current_user, "data_source_a_share", "YFINANCE"),
            hk_share=getattr(current_user, "data_source_hk_share", "YFINANCE"),
            us_share=getattr(current_user, "data_source_us_share", "YFINANCE"),
        ),
        available_sources=get_market_data_source_options()
    )


@router.put("/data-sources")
async def update_data_sources(
    update: DataSourceSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新分市场数据源配置"""
    user_repo = UserRepository(db)

    if update.a_share:
        if update.a_share not in SUPPORTED_DATA_SOURCES:
            raise HTTPException(status_code=400, detail="不支持的数据源")
        current_user.data_source_a_share = update.a_share

    if update.hk_share:
        if update.hk_share not in SUPPORTED_DATA_SOURCES:
            raise HTTPException(status_code=400, detail="不支持的数据源")
        current_user.data_source_hk_share = update.hk_share

    if update.us_share:
        if update.us_share not in SUPPORTED_DATA_SOURCES:
            raise HTTPException(status_code=400, detail="不支持的数据源")
        current_user.data_source_us_share = update.us_share

    await user_repo.save(current_user)

    return {"status": "success", "message": "数据源配置已更新"}
