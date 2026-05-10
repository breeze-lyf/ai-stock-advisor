import base64
import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """
    兼容层：
    - `send_feishu_card` 保留为底层飞书发送能力
    - 业务通知统一转发到 NotificationServiceV2
    """

    @staticmethod
    def _generate_signature(timestamp: int, secret: str) -> str:
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        return base64.b64encode(hmac_code).decode("utf-8")

    @staticmethod
    async def send_feishu_card(
        title: str,
        content: str,
        elements: Optional[List[Dict[str, Any]]] = None,
        color: str = "blue",
        webhook_url: Optional[str] = None,
        msg_type: str = "GENERAL",
        ticker: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        del msg_type, ticker, user_id

        url = webhook_url or settings.FEISHU_WEBHOOK_URL
        if not url:
            logger.warning("FEISHU_WEBHOOK_URL not configured, skipping notification.")
            return False

        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "template": color,
                    "title": {"content": title, "tag": "plain_text"},
                },
                "elements": elements or [{"tag": "div", "text": {"content": content, "tag": "lark_md"}}],
            },
        }
        if settings.FEISHU_SECRET:
            timestamp = int(time.time())
            payload["timestamp"] = str(timestamp)
            payload["sign"] = NotificationService._generate_signature(timestamp, settings.FEISHU_SECRET)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                return result.get("code") == 0
        except Exception as exc:
            logger.error("Failed to send Feishu notification: %s", exc)
            return False

    @staticmethod
    async def send_macro_alert(title: str, summary: str, heat_score: float, user_id: Optional[str] = None, webhook_url: Optional[str] = None):
        del webhook_url
        from app.services.notification_service_v2 import NotificationServiceV2

        if not user_id:
            return {"sent_channels": [], "skipped_channels": [], "blocked_reason": "missing_user_id"}
        return await NotificationServiceV2.send_macro_alert(user_id=user_id, title=title, summary=summary, heat_score=heat_score)

    @staticmethod
    async def send_macro_summary(topics_count: int, topics_list: List[Any], user_id: Optional[str] = None, webhook_url: Optional[str] = None):
        del webhook_url
        from app.services.notification_service_v2 import NotificationServiceV2

        if not user_id:
            return {"sent_channels": [], "skipped_channels": [], "blocked_reason": "missing_user_id"}
        return await NotificationServiceV2.send_macro_summary(user_id=user_id, topics_count=topics_count, topics_list=topics_list)

    @staticmethod
    async def send_price_alert(ticker: str, name: str, current_price: float, target_price: float, is_stop_loss: bool = False, user_id: Optional[str] = None, webhook_url: Optional[str] = None):
        del webhook_url
        from app.services.notification_service_v2 import NotificationServiceV2

        if not user_id:
            return {"sent_channels": [], "skipped_channels": [], "blocked_reason": "missing_user_id"}
        return await NotificationServiceV2.send_price_alert(
            user_id=user_id,
            ticker=ticker,
            name=name,
            current_price=current_price,
            target_price=target_price,
            is_stop_loss=is_stop_loss,
        )

    @staticmethod
    async def send_hourly_summary(summary_text: str, count: int, sentiment: str = "中性", email: str = "", user_id: Optional[str] = None, webhook_url: Optional[str] = None):
        del webhook_url
        from app.services.notification_service_v2 import NotificationServiceV2

        if not user_id:
            return {"sent_channels": [], "skipped_channels": [], "blocked_reason": "missing_user_id"}
        return await NotificationServiceV2.send_hourly_summary(
            user_id=user_id,
            summary_text=summary_text,
            count=count,
            sentiment=sentiment,
            email=email,
        )

    @staticmethod
    async def send_strategy_change_alert(
        ticker: str,
        name: str,
        old_strategy: Dict[str, Any],
        new_strategy: Dict[str, Any],
        change_reason: str,
        user_id: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ):
        del webhook_url
        from app.services.notification_service_v2 import NotificationServiceV2

        if not user_id:
            return {"sent_channels": [], "skipped_channels": [], "blocked_reason": "missing_user_id"}
        return await NotificationServiceV2.send_strategy_change_alert(
            user_id=user_id,
            ticker=ticker,
            name=name,
            old_strategy=old_strategy,
            new_strategy=new_strategy,
            change_reason=change_reason,
        )
