"""
统一通知编排层

职责：
1. 统一通知类型 -> 用户偏好 -> 优先级 -> 渠道路由
2. 统一静默时段、频控、去重与历史记录
3. 为业务层提供语义化的通知发送方法
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, time as dt_time, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.notification import NotificationLog
from app.models.notification_settings import (
    BrowserPushSubscription,
    NotificationPriority,
    UserNotificationSetting,
    UserNotificationSubscription,
)
from app.models.user import User
from app.services.integrations.email_service import EmailService
from app.utils.time import utc_now_naive

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotificationPolicy:
    preference_field: str | None
    default_priority: NotificationPriority
    dedupe_window: timedelta


POLICIES: dict[str, NotificationPolicy] = {
    "price_alert": NotificationPolicy("enable_price_alerts", NotificationPriority.P1, timedelta(hours=24)),
    "indicator_alert": NotificationPolicy("enable_indicator_alerts", NotificationPriority.P2, timedelta(hours=24)),
    "hourly_news_summary": NotificationPolicy("enable_hourly_summary", NotificationPriority.P3, timedelta(minutes=30)),
    "daily_report": NotificationPolicy("enable_daily_report", NotificationPriority.P2, timedelta(hours=8)),
    "macro_alert": NotificationPolicy("enable_macro_alerts", NotificationPriority.P1, timedelta(hours=1)),
    "macro_summary": NotificationPolicy("enable_macro_alerts", NotificationPriority.P2, timedelta(minutes=30)),
    "strategy_change": NotificationPolicy("enable_strategy_change_alerts", NotificationPriority.P1, timedelta(hours=12)),
    "test": NotificationPolicy(None, NotificationPriority.P2, timedelta()),
}


class NotificationServiceV2:
    @staticmethod
    async def send_notification(
        db: AsyncSession,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority | None = None,
        notification_type: Optional[str] = None,
        ticker: Optional[str] = None,
        target_id: Optional[str] = None,
        semantic_key: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        feishu_elements: Optional[List[Dict[str, Any]]] = None,
        feishu_color: Optional[str] = None,
        dedupe_window: Optional[timedelta] = None,
    ) -> Dict[str, Any]:
        notification_type = (notification_type or "general").strip().lower()
        policy = POLICIES.get(notification_type, NotificationPolicy(None, NotificationPriority.P2, timedelta(hours=24)))
        effective_priority = priority or policy.default_priority
        target_id = (target_id or ticker or notification_type).strip()
        semantic_key = (semantic_key or target_id).strip()
        dedupe_window = dedupe_window if dedupe_window is not None else policy.dedupe_window

        result = {
            "sent_channels": [],
            "skipped_channels": [],
            "blocked_reason": None,
        }

        user = await db.get(User, user_id)
        if not user:
            result["blocked_reason"] = "user_not_found"
            return result

        if not getattr(user, "notifications_enabled", True):
            result["blocked_reason"] = "notifications_disabled"
            return result

        preference_field = policy.preference_field
        if preference_field and hasattr(user, preference_field) and not getattr(user, preference_field, True):
            result["blocked_reason"] = f"{preference_field}_disabled"
            return result

        user_setting = await NotificationServiceV2._get_or_create_user_setting(db, user_id)

        if effective_priority in {NotificationPriority.P2, NotificationPriority.P3} and NotificationServiceV2._is_quiet_period(user_setting, user):
            result["blocked_reason"] = "quiet_period"
            return result

        if dedupe_window > timedelta() and await NotificationServiceV2._is_duplicate(
            db=db,
            user_id=user_id,
            notification_type=notification_type,
            target_id=target_id,
            semantic_key=semantic_key,
            dedupe_window=dedupe_window,
        ):
            result["blocked_reason"] = "deduplicated"
            return result

        if effective_priority != NotificationPriority.P0 and await NotificationServiceV2._check_daily_limit(
            db=db,
            user=user,
            user_setting=user_setting,
            priority=effective_priority,
        ):
            result["blocked_reason"] = "daily_limit_exceeded"
            result["skipped_channels"].append("all")
            return result

        channels_to_send = NotificationServiceV2._get_channels_for_priority(user_setting, effective_priority)
        if not channels_to_send:
            result["blocked_reason"] = "no_enabled_channels"
            return result

        for channel in channels_to_send:
            sent = False
            try:
                if channel == "feishu":
                    sent = await NotificationServiceV2._send_feishu(
                        user=user,
                        title=title,
                        message=message,
                        priority=effective_priority,
                        ticker=ticker,
                        extra_data=extra_data,
                        elements=feishu_elements,
                        color=feishu_color,
                    )
                elif channel == "browser":
                    sent = await NotificationServiceV2._send_browser_push(
                        db=db,
                        user_id=user_id,
                        title=title,
                        message=message,
                        priority=effective_priority,
                        ticker=ticker,
                        extra_data=extra_data,
                    )
                elif channel == "email":
                    sent = await NotificationServiceV2._send_email(
                        user=user,
                        title=title,
                        message=message,
                        priority=effective_priority,
                        ticker=ticker,
                    )
                elif channel == "sms":
                    result["skipped_channels"].append("sms_not_implemented")
                    continue
            except Exception as exc:
                logger.error("Failed to send %s notification to %s: %s", notification_type, channel, exc)
                result["skipped_channels"].append(f"{channel}_error")
                continue

            if sent:
                result["sent_channels"].append(channel)
            else:
                result["skipped_channels"].append(f"{channel}_unavailable")

        if result["sent_channels"]:
            await NotificationServiceV2._record_notification_sent(
                db=db,
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                ticker=ticker,
                target_id=target_id,
                semantic_key=semantic_key,
                priority=effective_priority,
                result=result,
                extra_data=extra_data,
            )
        elif result["blocked_reason"] is None:
            result["blocked_reason"] = "delivery_unavailable"

        return result

    @staticmethod
    async def send_price_alert(
        user_id: str,
        ticker: str,
        name: str,
        current_price: float,
        target_price: float,
        is_stop_loss: bool = False,
    ) -> Dict[str, Any]:
        priority = NotificationPriority.P0 if is_stop_loss else NotificationPriority.P1
        title_prefix = "⚠️ 触发止损警戒" if is_stop_loss else "🚀 达成止盈目标"
        action_name = "止损警戒位" if is_stop_loss else "止盈目标位"
        color = "red" if is_stop_loss else "green"
        currency = "USD" if not (ticker.isdigit() and len(ticker) == 6) else "CNY"
        semantic_key = f"{'stop_loss' if is_stop_loss else 'take_profit'}:{target_price:.4f}"

        elements = [
            {
                "tag": "div",
                "fields": [
                    {"is_short": True, "text": {"content": f"**证券代码**: {ticker}", "tag": "lark_md"}},
                    {"is_short": True, "text": {"content": f"**证券名称**: {name}", "tag": "lark_md"}},
                ],
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "content": (
                        f"**当前市价**: {currency} {current_price:,.2f}\n"
                        f"**目标建议 ({action_name})**: {currency} {target_price:,.2f}"
                    ),
                    "tag": "lark_md",
                },
            },
        ]

        async with SessionLocal() as db:
            return await NotificationServiceV2.send_notification(
                db=db,
                user_id=user_id,
                title=f"{title_prefix}: {ticker}",
                message=f"{name} ({ticker}) 已触达{action_name}",
                priority=priority,
                notification_type="price_alert",
                ticker=ticker,
                target_id=ticker,
                semantic_key=semantic_key,
                extra_data={"name": name, "current_price": current_price, "target_price": target_price, "is_stop_loss": is_stop_loss},
                feishu_elements=elements,
                feishu_color=color,
            )

    @staticmethod
    async def send_indicator_alert(
        user_id: str,
        ticker: str,
        stock_name: str,
        rsi_value: float,
        alert_side: str,
    ) -> Dict[str, Any]:
        side = "overbought" if alert_side == "overbought" else "oversold"
        title = f"⚠️ 指标超买警报: {stock_name}" if side == "overbought" else f"🟢 指标超卖警报: {stock_name}"
        message = (
            f"**{stock_name} ({ticker})** RSI(14) 已飙升至 `{rsi_value:.2f}`，处于严重超买区间。"
            if side == "overbought"
            else f"**{stock_name} ({ticker})** RSI(14) 已跌至 `{rsi_value:.2f}`，处于严重超卖状态。"
        )

        async with SessionLocal() as db:
            return await NotificationServiceV2.send_notification(
                db=db,
                user_id=user_id,
                title=title,
                message=message,
                notification_type="indicator_alert",
                ticker=ticker,
                target_id=ticker,
                semantic_key=f"rsi14:{side}",
                extra_data={"rsi_14": round(rsi_value, 2), "side": side},
                feishu_color="red" if side == "overbought" else "green",
            )

    @staticmethod
    async def send_hourly_summary(
        user_id: str,
        summary_text: str,
        count: int,
        sentiment: str = "中性",
        email: str = "",
        hour_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        sentiment_icon = "📈" if "利好" in sentiment else "📉" if "利空" in sentiment else "⚖️"
        elements = [
            {
                "tag": "div",
                "text": {
                    "content": f"📊 **本小时快讯回顾**: 共计抓取 `{count}` 条实时资讯。\n市场情绪倾向: {sentiment_icon} **{sentiment}**",
                    "tag": "lark_md",
                },
            },
            {"tag": "hr"},
            {"tag": "div", "text": {"content": f"**AI 核心研判**:\n{summary_text}", "tag": "lark_md"}},
            {"tag": "note", "elements": [{"tag": "plain_text", "content": f"账号归属: {email}\n建议操作：请结合个股诊断功能进行深度分析。"}]},
        ]

        async with SessionLocal() as db:
            return await NotificationServiceV2.send_notification(
                db=db,
                user_id=user_id,
                title="⏰ 财联社每小时新闻精要",
                message=summary_text,
                priority=NotificationPriority.P3,
                notification_type="hourly_news_summary",
                target_id="hourly_summary",
                semantic_key=hour_key or datetime.now(timezone.utc).strftime("%Y-%m-%d-%H"),
                extra_data={"count": count, "sentiment": sentiment},
                feishu_elements=elements,
                feishu_color="blue",
            )

    @staticmethod
    async def send_daily_report(
        user_id: str,
        detailed_report: str,
        report_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        async with SessionLocal() as db:
            return await NotificationServiceV2.send_notification(
                db=db,
                user_id=user_id,
                title="📅 每日持仓全景体检报告",
                message=f"**当前持仓摘要**:\n{detailed_report[:800]}...",
                priority=NotificationPriority.P2,
                notification_type="daily_report",
                target_id="daily_portfolio_report",
                semantic_key=report_date or datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"),
                extra_data={"excerpt": detailed_report[:800]},
                feishu_color="blue",
            )

    @staticmethod
    async def send_macro_alert(
        user_id: str,
        title: str,
        summary: str,
        heat_score: float,
        topic_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        priority = NotificationPriority.P0 if heat_score >= 95 else NotificationPriority.P1
        elements = [
            {"tag": "div", "text": {"content": f"**🔍 宏观热点探测**\n热度值: `{heat_score}`", "tag": "lark_md"}},
            {"tag": "hr"},
            {"tag": "div", "text": {"content": f"**摘要**: {summary}", "tag": "lark_md"}},
        ]

        async with SessionLocal() as db:
            return await NotificationServiceV2.send_notification(
                db=db,
                user_id=user_id,
                title=f"🔥 全球异动雷达: {title}",
                message=summary,
                priority=priority,
                notification_type="macro_alert",
                target_id=topic_id or title,
                semantic_key=f"macro_alert:{topic_id or title}",
                extra_data={"heat_score": heat_score},
                feishu_elements=elements,
                feishu_color="red" if heat_score >= 90 else "orange",
                dedupe_window=timedelta(hours=1),
            )

    @staticmethod
    async def send_macro_summary(
        user_id: str,
        topics_count: int,
        topics_list: List[Any],
        summary_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        topic_items: list[dict[str, Any]] = []
        for topic in topics_list:
            heat_color = "🔴" if topic.heat_score >= 90 else "🟠" if topic.heat_score >= 80 else "⚪"
            topic_items.append(
                {
                    "tag": "div",
                    "text": {
                        "content": f"{heat_color} **{topic.title}** (热度: `{topic.heat_score}`)\n{topic.summary[:100]}...",
                        "tag": "lark_md",
                    },
                }
            )
            topic_items.append({"tag": "hr"})

        elements = [
            {"tag": "div", "text": {"content": f"🎯 **全网扫描完成**: 本轮探测到 `{topics_count}` 个重要宏观热点。", "tag": "lark_md"}},
            {"tag": "hr"},
            *topic_items[:-1],
        ]

        async with SessionLocal() as db:
            return await NotificationServiceV2.send_notification(
                db=db,
                user_id=user_id,
                title="🌐 全球宏观热点扫描简报",
                message="每日宏观动态汇总",
                priority=NotificationPriority.P2,
                notification_type="macro_summary",
                target_id="macro_summary",
                semantic_key=summary_key or datetime.now(timezone.utc).strftime("%Y-%m-%d-%H-%M"),
                extra_data={"topics_count": topics_count},
                feishu_elements=elements,
                feishu_color="blue",
                dedupe_window=timedelta(minutes=30),
            )

    @staticmethod
    async def send_strategy_change_alert(
        user_id: str,
        ticker: str,
        name: str,
        old_strategy: Dict[str, Any],
        new_strategy: Dict[str, Any],
        change_reason: str,
    ) -> Dict[str, Any]:
        level = 2
        title_prefix = "🔔 策略动态更新"
        color = "blue"

        if old_strategy.get("action") != new_strategy.get("action"):
            level = 1
            title_prefix = "🚨 核心策略转向"
            color = "orange"

        old_rr_grade = old_strategy.get("rr_grade", "中性")
        new_rr_grade = new_strategy.get("rr_grade", "中性")
        if old_rr_grade != new_rr_grade and "低性价比" in str(new_rr_grade):
            level = 1
            title_prefix = "⚠️ 风险收益比恶化"
            color = "red"

        elements = [
            {"tag": "div", "text": {"content": f"**证券**: {name} ({ticker})\n**调整级别**: Level {level}", "tag": "lark_md"}},
            {"tag": "hr"},
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {
                            "content": (
                                f"**原建议**: {old_strategy.get('action', '无')}\n"
                                f"**原目标**: {old_strategy.get('target', '无')}\n"
                                f"**原止损**: {old_strategy.get('stop_loss', '无')}"
                            ),
                            "tag": "lark_md",
                        },
                    },
                    {
                        "is_short": True,
                        "text": {
                            "content": (
                                f"**新建议**: **{new_strategy.get('action', '无')}**\n"
                                f"**新目标**: **{new_strategy.get('target', '无')}**\n"
                                f"**新止损**: **{new_strategy.get('stop_loss', '无')}**"
                            ),
                            "tag": "lark_md",
                        },
                    },
                ],
            },
            {"tag": "div", "text": {"content": f"**变更原因**: {change_reason}", "tag": "lark_md"}},
        ]

        async with SessionLocal() as db:
            return await NotificationServiceV2.send_notification(
                db=db,
                user_id=user_id,
                title=f"{title_prefix}: {ticker}",
                message=f"{name} 策略发生调整",
                priority=NotificationPriority.P1 if level == 1 else NotificationPriority.P2,
                notification_type="strategy_change",
                ticker=ticker,
                target_id=ticker,
                semantic_key=f"strategy_change:{change_reason}",
                extra_data={"change_reason": change_reason, "level": level, "old_strategy": old_strategy, "new_strategy": new_strategy},
                feishu_elements=elements,
                feishu_color=color,
            )

    @staticmethod
    async def _get_or_create_user_setting(db: AsyncSession, user_id: str) -> UserNotificationSetting:
        stmt = select(UserNotificationSetting).where(UserNotificationSetting.user_id == user_id)
        result = await db.execute(stmt)
        setting = result.scalar_one_or_none()
        if setting:
            return setting

        setting = UserNotificationSetting(user_id=user_id)
        db.add(setting)
        try:
            await db.commit()
            await db.refresh(setting)
            return setting
        except IntegrityError:
            await db.rollback()
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                return existing
            raise

    @staticmethod
    def _is_quiet_period(user_setting: UserNotificationSetting, user: User) -> bool:
        if not user_setting.quiet_mode_enabled or not user_setting.quiet_mode_start or not user_setting.quiet_mode_end:
            return False

        try:
            zone = ZoneInfo(user.timezone or "Asia/Shanghai")
        except Exception:
            zone = ZoneInfo("Asia/Shanghai")

        try:
            now = datetime.now(zone).time()
            quiet_start = dt_time.fromisoformat(user_setting.quiet_mode_start)
            quiet_end = dt_time.fromisoformat(user_setting.quiet_mode_end)
        except Exception:
            return False

        if quiet_start <= quiet_end:
            return quiet_start <= now <= quiet_end
        return now >= quiet_start or now <= quiet_end

    @staticmethod
    async def _is_duplicate(
        db: AsyncSession,
        user_id: str,
        notification_type: str,
        target_id: str,
        semantic_key: str,
        dedupe_window: timedelta,
    ) -> bool:
        since = utc_now_naive() - dedupe_window
        stmt = select(NotificationLog.id).where(
            NotificationLog.user_id == user_id,
            NotificationLog.type == notification_type,
            NotificationLog.target_id == target_id,
            NotificationLog.semantic_key == semantic_key,
            NotificationLog.status == "SUCCESS",
            NotificationLog.created_at >= since,
        ).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def _check_daily_limit(
        db: AsyncSession,
        user: User,
        user_setting: UserNotificationSetting,
        priority: NotificationPriority,
    ) -> bool:
        limit_field = f"{priority.value.lower()}_daily_limit"
        limit_value = getattr(user_setting, limit_field, None)
        if limit_value is None or limit_value <= 0:
            return False

        try:
            zone = ZoneInfo(user.timezone or "Asia/Shanghai")
        except Exception:
            zone = ZoneInfo("Asia/Shanghai")

        local_now = datetime.now(zone)
        local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        utc_start = local_start.astimezone(timezone.utc).replace(tzinfo=None)

        stmt = select(func.count(NotificationLog.id)).where(
            NotificationLog.user_id == user.id,
            NotificationLog.priority == priority.value,
            NotificationLog.status == "SUCCESS",
            NotificationLog.created_at >= utc_start,
        )
        result = await db.execute(stmt)
        sent_count = int(result.scalar() or 0)
        return sent_count >= limit_value

    @staticmethod
    def _get_channels_for_priority(
        user_setting: UserNotificationSetting,
        priority: NotificationPriority,
    ) -> List[str]:
        channels: list[str] = []

        if user_setting.feishu_enabled:
            channels.append("feishu")
        if user_setting.browser_push_enabled:
            channels.append("browser")
        if user_setting.email_enabled:
            channels.append("email")

        if priority == NotificationPriority.P0 and user_setting.sms_enabled:
            channels.append("sms")

        return channels

    @staticmethod
    async def _send_feishu(
        user: User,
        title: str,
        message: str,
        priority: NotificationPriority,
        ticker: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        elements: Optional[List[Dict[str, Any]]] = None,
        color: Optional[str] = None,
    ) -> bool:
        webhook_url = user.feishu_webhook_url or settings.FEISHU_WEBHOOK_URL
        if not webhook_url:
            return False

        timestamp = int(time.time())
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": color or {
                    NotificationPriority.P0: "red",
                    NotificationPriority.P1: "orange",
                    NotificationPriority.P2: "blue",
                    NotificationPriority.P3: "grey",
                }.get(priority, "blue"),
                "title": {"content": title, "tag": "plain_text"},
            },
            "elements": elements or [{"tag": "div", "text": {"content": message, "tag": "lark_md"}}],
        }

        if ticker or extra_data:
            metadata = []
            if ticker:
                metadata.append(f"标的: {ticker}")
            if extra_data:
                metadata.append(f"附加信息: {json.dumps(extra_data, ensure_ascii=False)}")
            card["elements"].append({"tag": "note", "elements": [{"tag": "plain_text", "content": " | ".join(metadata)}]})

        payload = {"msg_type": "interactive", "card": card}
        if settings.FEISHU_SECRET:
            payload["timestamp"] = str(timestamp)
            payload["sign"] = NotificationServiceV2._generate_signature(timestamp, settings.FEISHU_SECRET)

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            body = response.json()
            return body.get("code") == 0

    @staticmethod
    async def _send_browser_push(
        db: AsyncSession,
        user_id: str,
        title: str,
        message: str,
        priority: NotificationPriority,
        ticker: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        stmt = select(BrowserPushSubscription).where(BrowserPushSubscription.user_id == user_id)
        result = await db.execute(stmt)
        subscriptions = result.scalars().all()
        if not subscriptions:
            return False

        try:
            from pywebpush import webpush
        except ImportError:
            logger.warning("pywebpush not installed, skipping browser push")
            return False

        payload = json.dumps(
            {
                "title": title,
                "body": message,
                "priority": priority.value,
                "ticker": ticker,
                "data": extra_data or {},
            }
        )

        delivered = False
        for subscription in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": subscription.endpoint,
                        "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                    },
                    data=payload,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": f"mailto:{settings.WEB_PUSH_CONTACT_EMAIL or 'admin@example.com'}"},
                )
                delivered = True
            except Exception as exc:
                logger.error("Failed to send browser push: %s", exc)
        return delivered

    @staticmethod
    async def _send_email(
        user: User,
        title: str,
        message: str,
        priority: NotificationPriority,
        ticker: Optional[str] = None,
    ) -> bool:
        if not user.email:
            return False

        html_content = f"""
        <html>
        <body>
            <h2>{title}</h2>
            <p>{message}</p>
            {f'<p><strong>股票代码:</strong> {ticker}</p>' if ticker else ''}
            <hr/>
            <p style="color: gray; font-size: 12px;">优先级：{priority.value} | AI Smart Investment Advisor</p>
        </body>
        </html>
        """
        return await EmailService.send_email(
            to_emails=[user.email],
            subject=f"[{priority.value}] {title}",
            html_content=html_content,
        )

    @staticmethod
    async def _record_notification_sent(
        db: AsyncSession,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        ticker: Optional[str],
        target_id: str,
        semantic_key: str,
        priority: NotificationPriority,
        result: Dict[str, Any],
        extra_data: Optional[Dict[str, Any]],
    ) -> None:
        log = NotificationLog(
            user_id=user_id,
            ticker=ticker,
            type=notification_type,
            target_id=target_id,
            semantic_key=semantic_key,
            priority=priority.value,
            title=title,
            content=message,
            card_payload={"result": result, "extra_data": extra_data or {}},
            status="SUCCESS",
        )
        db.add(log)
        await db.commit()

    @staticmethod
    def _generate_signature(timestamp: int, secret: str) -> str:
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        return base64.b64encode(hmac_code).decode("utf-8")

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
        stmt = select(UserNotificationSubscription).where(
            UserNotificationSubscription.id == subscription_id,
            UserNotificationSubscription.user_id == user_id,
        )
        result = await db.execute(stmt)
        subscription = result.scalar_one_or_none()
        if not subscription:
            return False
        await db.delete(subscription)
        await db.commit()
        return True

    @staticmethod
    async def get_subscriptions(
        db: AsyncSession,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        stmt = select(UserNotificationSubscription).where(
            UserNotificationSubscription.user_id == user_id,
            UserNotificationSubscription.is_active == True,
        )
        result = await db.execute(stmt)
        subscriptions = result.scalars().all()
        return [
            {
                "id": item.id,
                "subscription_type": item.subscription_type,
                "target_id": item.target_id,
                "enable_price_alert": item.enable_price_alert,
                "enable_analysis_complete": item.enable_analysis_complete,
                "enable_news": item.enable_news,
                "price_alert_above": float(item.price_alert_above) if item.price_alert_above else None,
                "price_alert_below": float(item.price_alert_below) if item.price_alert_below else None,
            }
            for item in subscriptions
        ]

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
        stmt = select(BrowserPushSubscription).where(BrowserPushSubscription.endpoint == endpoint)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.last_used_at = utc_now_naive()
            await db.commit()
            await db.refresh(existing)
            return existing

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
        stmt = select(BrowserPushSubscription).where(
            BrowserPushSubscription.id == subscription_id,
            BrowserPushSubscription.user_id == user_id,
        )
        result = await db.execute(stmt)
        subscription = result.scalar_one_or_none()
        if not subscription:
            return False
        await db.delete(subscription)
        await db.commit()
        return True

    @staticmethod
    async def unsubscribe_browser_push_by_endpoint(
        db: AsyncSession,
        user_id: str,
        endpoint: str,
    ) -> bool:
        stmt = select(BrowserPushSubscription).where(
            BrowserPushSubscription.user_id == user_id,
            BrowserPushSubscription.endpoint == endpoint,
        )
        result = await db.execute(stmt)
        subscription = result.scalar_one_or_none()
        if not subscription:
            return False
        await db.delete(subscription)
        await db.commit()
        return True


notification_service_v2 = NotificationServiceV2()
