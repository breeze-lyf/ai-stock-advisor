"""
通知设置 API
管理用户通知偏好、订阅和浏览器推送
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.notification_settings import (
    UserNotificationSetting,
    UserNotificationSubscription,
    BrowserPushSubscription,
    NotificationPriority,
)
from app.services.notification_service_v2 import notification_service_v2

router = APIRouter()


@router.get("/notification-settings")
async def get_notification_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的通知设置"""
    stmt = select(UserNotificationSetting).where(
        UserNotificationSetting.user_id == current_user.id
    )
    db_result = await db.execute(stmt)
    setting = db_result.scalar_one_or_none()

    if not setting:
        # 返回默认设置
        return {
            "status": "success",
            "settings": {
                "email_enabled": False,
                "feishu_enabled": True,
                "browser_push_enabled": False,
                "sms_enabled": False,
                "quiet_mode_enabled": False,
                "quiet_mode_start": None,
                "quiet_mode_end": None,
                "p0_daily_limit": 999,
                "p1_daily_limit": 20,
                "p2_daily_limit": 5,
                "p3_daily_limit": 10,
            },
        }

    return {
        "status": "success",
        "settings": {
            "email_enabled": setting.email_enabled,
            "feishu_enabled": setting.feishu_enabled,
            "browser_push_enabled": setting.browser_push_enabled,
            "sms_enabled": setting.sms_enabled,
            "quiet_mode_enabled": setting.quiet_mode_enabled,
            "quiet_mode_start": setting.quiet_mode_start,
            "quiet_mode_end": setting.quiet_mode_end,
            "p0_daily_limit": setting.p0_daily_limit,
            "p1_daily_limit": setting.p1_daily_limit,
            "p2_daily_limit": setting.p2_daily_limit,
            "p3_daily_limit": setting.p3_daily_limit,
        },
    }


@router.patch("/notification-settings")
async def update_notification_settings(
    email_enabled: Optional[bool] = Query(None),
    feishu_enabled: Optional[bool] = Query(None),
    browser_push_enabled: Optional[bool] = Query(None),
    sms_enabled: Optional[bool] = Query(None),
    quiet_mode_enabled: Optional[bool] = Query(None),
    quiet_mode_start: Optional[str] = Query(None),
    quiet_mode_end: Optional[str] = Query(None),
    p0_daily_limit: Optional[int] = Query(None, ge=1),
    p1_daily_limit: Optional[int] = Query(None, ge=1),
    p2_daily_limit: Optional[int] = Query(None, ge=1),
    p3_daily_limit: Optional[int] = Query(None, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新用户通知设置"""
    stmt = select(UserNotificationSetting).where(
        UserNotificationSetting.user_id == current_user.id
    )
    db_result = await db.execute(stmt)
    setting = db_result.scalar_one_or_none()

    if not setting:
        # 创建新设置
        setting = UserNotificationSetting(user_id=current_user.id)
        db.add(setting)

    # 更新提供的字段
    if email_enabled is not None:
        setting.email_enabled = email_enabled
    if feishu_enabled is not None:
        setting.feishu_enabled = feishu_enabled
    if browser_push_enabled is not None:
        setting.browser_push_enabled = browser_push_enabled
    if sms_enabled is not None:
        setting.sms_enabled = sms_enabled
    if quiet_mode_enabled is not None:
        setting.quiet_mode_enabled = quiet_mode_enabled
    if quiet_mode_start is not None:
        setting.quiet_mode_start = quiet_mode_start
    if quiet_mode_end is not None:
        setting.quiet_mode_end = quiet_mode_end
    if p0_daily_limit is not None:
        setting.p0_daily_limit = p0_daily_limit
    if p1_daily_limit is not None:
        setting.p1_daily_limit = p1_daily_limit
    if p2_daily_limit is not None:
        setting.p2_daily_limit = p2_daily_limit
    if p3_daily_limit is not None:
        setting.p3_daily_limit = p3_daily_limit

    await db.commit()
    await db.refresh(setting)

    return {
        "status": "success",
        "settings": {
            "email_enabled": setting.email_enabled,
            "feishu_enabled": setting.feishu_enabled,
            "browser_push_enabled": setting.browser_push_enabled,
            "sms_enabled": setting.sms_enabled,
            "quiet_mode_enabled": setting.quiet_mode_enabled,
            "quiet_mode_start": setting.quiet_mode_start,
            "quiet_mode_end": setting.quiet_mode_end,
            "p0_daily_limit": setting.p0_daily_limit,
            "p1_daily_limit": setting.p1_daily_limit,
            "p2_daily_limit": setting.p2_daily_limit,
            "p3_daily_limit": setting.p3_daily_limit,
        },
    }


@router.get("/notification-settings/subscriptions")
async def get_subscriptions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的通知订阅列表"""
    subscriptions = await notification_service_v2.get_subscriptions(db, current_user.id)

    return {
        "status": "success",
        "subscriptions": subscriptions,
    }


@router.post("/notification-settings/subscriptions")
async def create_subscription(
    subscription_type: str = Query(..., description="订阅类型 (ticker/sector/topic)"),
    target_id: str = Query(..., description="订阅目标 (股票代码/行业/主题)"),
    enable_price_alert: bool = Query(True, description="启用价格预警"),
    enable_analysis_complete: bool = Query(True, description="启用 AI 分析完成通知"),
    enable_news: bool = Query(False, description="启用相关新闻"),
    price_alert_above: Optional[float] = Query(None, description="突破某价格时提醒"),
    price_alert_below: Optional[float] = Query(None, description="跌破某价格时提醒"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建通知订阅"""
    subscription = await notification_service_v2.subscribe(
        db=db,
        user_id=current_user.id,
        subscription_type=subscription_type,
        target_id=target_id,
        enable_price_alert=enable_price_alert,
        enable_analysis_complete=enable_analysis_complete,
        enable_news=enable_news,
        price_alert_above=price_alert_above,
        price_alert_below=price_alert_below,
    )

    return {
        "status": "success",
        "subscription": {
            "id": subscription.id,
            "subscription_type": subscription.subscription_type,
            "target_id": subscription.target_id,
            "enable_price_alert": subscription.enable_price_alert,
            "enable_analysis_complete": subscription.enable_analysis_complete,
            "enable_news": subscription.enable_news,
            "price_alert_above": subscription.price_alert_above,
            "price_alert_below": subscription.price_alert_below,
        },
    }


@router.delete("/notification-settings/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """取消通知订阅"""
    success = await notification_service_v2.unsubscribe(db, current_user.id, subscription_id)

    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return {"status": "success"}


@router.post("/notification-settings/browser-push/subscribe")
async def subscribe_browser_push(
    endpoint: str,
    p256dh: str,
    auth: str,
    device_name: Optional[str] = None,
    browser: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    订阅浏览器推送

    前端使用 Web Push API 创建订阅后，将 subscription 信息发送到本接口
    """
    subscription = await notification_service_v2.subscribe_browser_push(
        db=db,
        user_id=current_user.id,
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth,
        device_name=device_name,
        browser=browser,
    )

    return {
        "status": "success",
        "subscription": {
            "id": subscription.id,
            "endpoint": subscription.endpoint[:50] + "...",  # 不返回完整 endpoint
            "device_name": subscription.device_name,
            "browser": subscription.browser,
            "created_at": subscription.created_at.isoformat(),
        },
    }


@router.delete("/notification-settings/browser-push/{subscription_id}")
async def unsubscribe_browser_push(
    subscription_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """取消浏览器推送订阅"""
    success = await notification_service_v2.unsubscribe_browser_push(
        db, current_user.id, subscription_id
    )

    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return {"status": "success"}


@router.get("/notification-settings/browser-push")
async def get_browser_push_subscriptions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的浏览器推送订阅列表"""
    stmt = select(BrowserPushSubscription).where(
        BrowserPushSubscription.user_id == current_user.id
    )
    db_result = await db.execute(stmt)
    subscriptions = db_result.scalars().all()

    return {
        "status": "success",
        "subscriptions": [
            {
                "id": s.id,
                "device_name": s.device_name,
                "browser": s.browser,
                "created_at": s.created_at.isoformat(),
                "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None,
            }
            for s in subscriptions
        ],
    }


@router.post("/notification-settings/test")
async def test_notification(
    priority: str = Query("P2", description="通知优先级 (P0/P1/P2/P3)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发送测试通知"""
    try:
        priority_enum = NotificationPriority(priority.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid priority. Use P0, P1, P2, or P3")

    result = await notification_service_v2.send_notification(
        db=db,
        user_id=current_user.id,
        title="测试通知",
        message=f"这是一条 {priority_enum.value} 优先级的测试通知",
        priority=priority_enum,
        notification_type="test",
    )

    return {
        "status": "success",
        "result": result,
    }
