"""
通知服务 V2
支持多渠道通知、智能分级推送、静默时段控制
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.notification_settings import (
    UserNotificationSetting,
    UserNotificationSubscription,
    BrowserPushSubscription,
    NotificationPriority,
)
from app.models.user import User
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService
from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationServiceV2:
    """
    通知服务 V2

    功能：
    1. 浏览器推送（Web Push API）
    2. 智能分级推送（P0/P1/P2/P3）
    3. 静默时段控制
    4. 每日频率限制
    5. 多渠道路由
    """

    # P0 紧急通知：发送到所有启用的渠道，不受静默时段和频率限制
    # P1 高优先级：发送到主要渠道（Feishu + Browser），不受静默时段限制
    # P2 中优先级：发送到主要渠道，受静默时段限制
    # P3 低优先级：仅在活跃时段发送，受频率限制

    @staticmethod
    async def send_notification(
        db: AsyncSession,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.P2,
        notification_type: Optional[str] = None,
        ticker: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        发送通知（智能路由）

        Args:
            db: 数据库会话
            user_id: 用户 ID
            title: 通知标题
            message: 通知内容
            priority: 通知优先级
            notification_type: 通知类型 (price_alert/analysis_complete/news/etc.)
            ticker: 关联股票代码
            extra_data: 额外数据

        Returns:
            {"sent_channels": [...], "skipped_channels": [...], "blocked_reason": ...}
        """
        result = {
            "sent_channels": [],
            "skipped_channels": [],
            "blocked_reason": None,
        }

        # 获取用户通知设置
        stmt = select(UserNotificationSetting).where(UserNotificationSetting.user_id == user_id)
        db_result = await db.execute(stmt)
        user_setting = db_result.scalar_one_or_none()

        if not user_setting:
            # 创建默认设置
            user_setting = UserNotificationSetting(user_id=user_id)
            db.add(user_setting)
            await db.commit()
            await db.refresh(user_setting)

        # 检查是否在静默时段
        is_quiet_period = NotificationServiceV2._is_quiet_period(user_setting)

        # 根据优先级和静默时段决定是否发送
        if priority == NotificationPriority.P0:
            # P0 紧急通知：跳过所有检查
            pass
        elif priority == NotificationPriority.P1:
            # P1 高优先级：跳过静默时段检查
            pass
        elif is_quiet_period:
            # P2/P3 在静默时段：跳过
            result["blocked_reason"] = "quiet_period"
            return result

        # 检查每日频率限制
        daily_limit_exceeded = await NotificationServiceV2._check_daily_limit(
            db, user_id, priority
        )
        if daily_limit_exceeded and priority != NotificationPriority.P0:
            result["blocked_reason"] = "daily_limit_exceeded"
            result["skipped_channels"].append("all")
            return result

        # 根据优先级确定发送渠道
        channels_to_send = NotificationServiceV2._get_channels_for_priority(
            user_setting, priority
        )

        # 发送通知到各渠道
        for channel in channels_to_send:
            try:
                if channel == "feishu" and user_setting.feishu_enabled:
                    await NotificationServiceV2._send_feishu(
                        title, message, priority, ticker, extra_data
                    )
                    result["sent_channels"].append("feishu")
                elif channel == "browser" and user_setting.browser_push_enabled:
                    await NotificationServiceV2._send_browser_push(
                        db, user_id, title, message, priority, ticker, extra_data
                    )
                    result["sent_channels"].append("browser")
                elif channel == "email" and user_setting.email_enabled:
                    await NotificationServiceV2._send_email(
                        db, user_id, title, message, priority, ticker, extra_data
                    )
                    result["sent_channels"].append("email")
                elif channel == "sms" and user_setting.sms_enabled:
                    # SMS 服务待实现
                    result["skipped_channels"].append("sms_not_implemented")
            except Exception as e:
                logger.error(f"Failed to send to {channel}: {e}")
                result["skipped_channels"].append(f"{channel}_error")

        # 记录发送历史（用于频率统计）
        await NotificationServiceV2._record_notification_sent(db, user_id, priority)

        return result

    @staticmethod
    async def _send_feishu(
        title: str,
        message: str,
        priority: NotificationPriority,
        ticker: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ):
        """发送飞书通知"""
        # 根据优先级添加不同标记
        color = {
            NotificationPriority.P0: "red",
            NotificationPriority.P1: "orange",
            NotificationPriority.P2: "blue",
            NotificationPriority.P3: "gray",
        }.get(priority, "gray")

        content = {
            "title": title,
            "text": message,
        }
        if ticker:
            content["ticker"] = ticker
        if extra_data:
            content.update(extra_data)

        await NotificationService.send_feishu_card(
            title=title,
            content=message,
            color=color,
        )

    @staticmethod
    async def _send_browser_push(
        db: AsyncSession,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority,
        ticker: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ):
        """发送浏览器推送"""
        # 获取用户的所有浏览器订阅
        stmt = select(BrowserPushSubscription).where(
            BrowserPushSubscription.user_id == user_id
        )
        db_result = await db.execute(stmt)
        subscriptions = db_result.scalars().all()

        if not subscriptions:
            return

        # 异步导入 pywebpush
        try:
            from pywebpush import webpush
            import json
        except ImportError:
            logger.warning("pywebpush not installed, skipping browser push")
            return

        notification_data = json.dumps({
            "title": title,
            "body": message,
            "priority": priority.value,
            "type": "notification",
            "ticker": ticker,
            "icon": "/icons/notification-icon.png",
            "badge": "/icons/badge-icon.png",
            "data": extra_data or {},
        })

        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub.endpoint,
                        "keys": {
                            "p256dh": sub.p256dh,
                            "auth": sub.auth,
                        },
                    },
                    data=notification_data,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={
                        "sub": f"mailto:{settings.WEB_PUSH_CONTACT_EMAIL or 'admin@example.com'}",
                    },
                )
                logger.info(f"Browser push sent to {sub.device_name or sub.id}")
            except Exception as e:
                logger.error(f"Failed to send browser push: {e}")

    @staticmethod
    async def _send_email(
        db: AsyncSession,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority,
        ticker: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ):
        """发送邮件通知"""
        # 获取用户邮箱
        stmt = select(User).where(User.id == user_id)
        db_result = await db.execute(stmt)
        user = db_result.scalar_one_or_none()

        if not user or not user.email:
            return

        # 构建邮件内容
        html_content = f"""
        <html>
        <body>
            <h2>{title}</h2>
            <p>{message}</p>
            {f'<p><strong>股票代码:</strong> {ticker}</p>' if ticker else ''}
            <hr/>
            <p style="color: gray; font-size: 12px;">
                优先级：{priority.value} | AI Smart Investment Advisor
            </p>
        </body>
        </html>
        """

        await EmailService.send_email(
            to_emails=[user.email],
            subject=f"[{priority.value}] {title}",
            html_content=html_content,
        )

    @staticmethod
    def _is_quiet_period(user_setting: UserNotificationSetting) -> bool:
        """检查当前是否在静默时段"""
        if not user_setting.quiet_mode_enabled:
            return False

        if not user_setting.quiet_mode_start or not user_setting.quiet_mode_end:
            return False

        try:
            now = datetime.now().time()
            quiet_start = time.fromisoformat(user_setting.quiet_mode_start)
            quiet_end = time.fromisoformat(user_setting.quiet_mode_end)

            # 处理跨天的情况（如 22:00 - 07:00）
            if quiet_start <= quiet_end:
                # 同一天内
                return quiet_start <= now <= quiet_end
            else:
                # 跨天（如 22:00 - 07:00）
                return now >= quiet_start or now <= quiet_end
        except Exception:
            return False

    @staticmethod
    async def _check_daily_limit(
        db: AsyncSession,
        user_id: str,
        priority: NotificationPriority,
    ) -> bool:
        """
        检查是否超过每日频率限制

        Returns:
            True = 已超过限制，False = 未超过
        """
        # TODO: 实现通知发送历史表和频率统计
        # 目前简化实现：总是返回 False（不限制）
        return False

    @staticmethod
    async def _record_notification_sent(
        db: AsyncSession,
        user_id: str,
        priority: NotificationPriority,
    ):
        """记录通知发送历史"""
        # TODO: 实现通知发送历史表
        pass

    @staticmethod
    def _get_channels_for_priority(
        user_setting: UserNotificationSetting,
        priority: NotificationPriority,
    ) -> List[str]:
        """根据优先级返回应该发送的渠道列表"""
        if priority == NotificationPriority.P0:
            # P0: 所有启用的渠道
            channels = []
            if user_setting.feishu_enabled:
                channels.append("feishu")
            if user_setting.browser_push_enabled:
                channels.append("browser")
            if user_setting.email_enabled:
                channels.append("email")
            if user_setting.sms_enabled:
                channels.append("sms")
            return channels
        elif priority == NotificationPriority.P1:
            # P1: Feishu + Browser
            channels = []
            if user_setting.feishu_enabled:
                channels.append("feishu")
            if user_setting.browser_push_enabled:
                channels.append("browser")
            return channels
        elif priority == NotificationPriority.P2:
            # P2: 仅 Browser
            if user_setting.browser_push_enabled:
                return ["browser"]
            return []
        else:
            # P3: 仅 Browser（且受更严格的频率限制）
            if user_setting.browser_push_enabled:
                return ["browser"]
            return []

    # ==================== 订阅管理 ====================

    @staticmethod
    async def subscribe(
        db: AsyncSession,
        user_id: str,
        subscription_type: str,
        target_id: str,
        enable_price_alert: bool = True,
        enable_analysis_complete: bool = True,
        enable_news: bool = False,
        price_alert_above: Optional[float] = None,
        price_alert_below: Optional[float] = None,
    ) -> UserNotificationSubscription:
        """创建订阅"""
        subscription = UserNotificationSubscription(
            user_id=user_id,
            subscription_type=subscription_type,
            target_id=target_id,
            enable_price_alert=enable_price_alert,
            enable_analysis_complete=enable_analysis_complete,
            enable_news=enable_news,
            price_alert_above=str(price_alert_above) if price_alert_above else None,
            price_alert_below=str(price_alert_below) if price_alert_below else None,
        )
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
        return subscription

    @staticmethod
    async def unsubscribe(
        db: AsyncSession,
        user_id: str,
        subscription_id: str,
    ) -> bool:
        """取消订阅"""
        stmt = select(UserNotificationSubscription).where(
            UserNotificationSubscription.id == subscription_id,
            UserNotificationSubscription.user_id == user_id,
        )
        db_result = await db.execute(stmt)
        subscription = db_result.scalar_one_or_none()

        if subscription:
            await db.delete(subscription)
            await db.commit()
            return True
        return False

    @staticmethod
    async def get_subscriptions(
        db: AsyncSession,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """获取用户的所有订阅"""
        stmt = select(UserNotificationSubscription).where(
            UserNotificationSubscription.user_id == user_id,
            UserNotificationSubscription.is_active == True,
        )
        db_result = await db.execute(stmt)
        subscriptions = db_result.scalars().all()

        return [
            {
                "id": s.id,
                "subscription_type": s.subscription_type,
                "target_id": s.target_id,
                "enable_price_alert": s.enable_price_alert,
                "enable_analysis_complete": s.enable_analysis_complete,
                "enable_news": s.enable_news,
                "price_alert_above": float(s.price_alert_above) if s.price_alert_above else None,
                "price_alert_below": float(s.price_alert_below) if s.price_alert_below else None,
            }
            for s in subscriptions
        ]

    # ==================== 浏览器推送订阅 ====================

    @staticmethod
    async def subscribe_browser_push(
        db: AsyncSession,
        user_id: str,
        endpoint: str,
        p256dh: str,
        auth: str,
        device_name: Optional[str] = None,
        browser: Optional[str] = None,
    ) -> BrowserPushSubscription:
        """订阅浏览器推送"""
        # 检查是否已存在相同的 endpoint
        stmt = select(BrowserPushSubscription).where(
            BrowserPushSubscription.endpoint == endpoint
        )
        db_result = await db.execute(stmt)
        existing = db_result.scalar_one_or_none()

        if existing:
            # 更新现有订阅
            existing.last_used_at = datetime.utcnow()
            await db.commit()
            await db.refresh(existing)
            return existing

        # 创建新订阅
        subscription = BrowserPushSubscription(
            user_id=user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            device_name=device_name,
            browser=browser,
        )
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
        return subscription

    @staticmethod
    async def unsubscribe_browser_push(
        db: AsyncSession,
        user_id: str,
        subscription_id: str,
    ) -> bool:
        """取消浏览器推送订阅"""
        stmt = select(BrowserPushSubscription).where(
            BrowserPushSubscription.id == subscription_id,
            BrowserPushSubscription.user_id == user_id,
        )
        db_result = await db.execute(stmt)
        subscription = db_result.scalar_one_or_none()

        if subscription:
            await db.delete(subscription)
            await db.commit()
            return True
        return False


# 全局单例
notification_service_v2 = NotificationServiceV2()
