import httpx
import logging
import json
import hmac
import hashlib
import base64
import time
from typing import Dict, Any, Optional, List
from app.core.config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    """
    负责系统各类通知推送 (Feishu/Lark Bot Integration)
    """
    
    @staticmethod
    def _generate_signature(timestamp: int, secret: str) -> str:
        """
        飞书 Webhook 安全校验签名生成
        """
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
        user_id: Optional[str] = None
    ) -> bool:
        """
        发送飞书富文本卡片消息，包含 24 小时去重逻辑
        """
        # --- 1. 24 小时去重检查 (带异常保护) ---
        from app.core.database import SessionLocal
        from app.models.notification import NotificationLog
        from sqlalchemy.future import select
        from datetime import datetime, timedelta

        try:
            async with SessionLocal() as db:
                # 定义需要跳过 24 小时严格去重的主动推送类型 (如每小时摘要、雷达汇总)
                # 这些类型应仅在 1 分钟内去重，防止并发冲突
                SKIP_24H_DEDUPE = ["MACRO_SUMMARY", "HOURLY_NEWS_SUMMARY"]
                
                one_day_ago = datetime.utcnow() - timedelta(hours=24 if msg_type not in SKIP_24H_DEDUPE else 0)
                # 对于跳过 24h 的类型，仍需 1 分钟防重
                one_min_ago = datetime.utcnow() - timedelta(minutes=1)
                
                check_threshold = one_day_ago if msg_type not in SKIP_24H_DEDUPE else one_min_ago

                stmt = select(NotificationLog).where(
                    NotificationLog.user_id == user_id,
                    NotificationLog.type == msg_type,
                    NotificationLog.ticker == ticker,
                    NotificationLog.status == "SUCCESS",
                    NotificationLog.created_at >= check_threshold
                )
                res = await db.execute(stmt)
                if res.scalars().first():
                    logger.info(f"Notification deduplication hit for user {user_id}: {msg_type} (Threshold: {msg_type not in SKIP_24H_DEDUPE})")
                    return True
        except Exception as db_e:
            # 数据库故障时不应阻塞推送，仅记录日志并继续
            logger.warning(f"Notification deduplication check failed (DB Error): {db_e}. Proceeding anyway.")

        # --- 2. 构建并发送 ---
        url = webhook_url or settings.FEISHU_WEBHOOK_URL
        if not url:
            logger.warning("FEISHU_WEBHOOK_URL not configured, skipping notification.")
            return False

        timestamp = int(time.time())
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": color,
                "title": {"content": title, "tag": "plain_text"}
            },
            "elements": elements or [
                {"tag": "div", "text": {"content": content, "tag": "lark_md"}}
            ]
        }
        card["elements"].append({
            "tag": "note",
            "elements": [{"tag": "plain_text", "content": f"通知周期: {time.strftime('%Y-%m-%d %H:%M:%S')}"}]
        })

        payload = {"msg_type": "interactive", "card": card}
        if settings.FEISHU_SECRET:
            payload["timestamp"] = str(timestamp)
            payload["sign"] = NotificationService._generate_signature(timestamp, settings.FEISHU_SECRET)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                result = response.json()
                if result.get("code") == 0:
                    logger.info(f"Feishu notification sent successfully: {title}")
                    # 记录成功日志
                    async with SessionLocal() as db:
                        log = NotificationLog(
                            user_id=user_id,
                            type=msg_type,
                            ticker=ticker,
                            title=title,
                            content=content or title,
                            card_payload=card,
                            status="SUCCESS"
                        )
                        db.add(log)
                        await db.commit()
                    return True
                else:
                    logger.error(f"Feishu API error: {result.get('msg')}")
                    return False
        except Exception as e:
            logger.error(f"Failed to send Feishu notification: {str(e)}")
            return False

    @staticmethod
    async def send_macro_alert(title: str, summary: str, heat_score: float, user_id: Optional[str] = None, webhook_url: Optional[str] = None):
        """
        发送宏观雷达预警
        """
        elements = [
            {
                "tag": "div",
                "text": {
                    "content": f"**🔍 宏观热点探测**\n热度值: `{heat_score}`",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "div",
                "text": {
                    "content": f"**摘要**: {summary}",
                    "tag": "lark_md"
                }
            }
        ]
        
        return await NotificationService.send_feishu_card(
            title=f"🔥 全球异动雷达: {title}",
            content=summary,
            elements=elements,
            color="red" if heat_score > 90 else "orange",
            msg_type="MACRO_ALERT",
            user_id=user_id,
            webhook_url=webhook_url
        )

    @staticmethod
    async def send_macro_summary(topics_count: int, topics_list: List[Any], user_id: Optional[str] = None, webhook_url: Optional[str] = None):
        """
        发送宏观热点扫描汇总简报
        """
        topic_items = []
        for t in topics_list:
            heat_color = "🔴" if t.heat_score >= 90 else "🟠" if t.heat_score >= 80 else "⚪"
            topic_items.append({
                "tag": "div",
                "text": {
                    "content": f"{heat_color} **{t.title}** (热度: `{t.heat_score}`)\n{t.summary[:100]}...",
                    "tag": "lark_md"
                }
            })
            topic_items.append({"tag": "hr"})

        elements = [
            {
                "tag": "div",
                "text": {
                    "content": f"🎯 **全网扫描完成**: 本轮探测到 `{topics_count}` 个重要宏观热点。",
                    "tag": "lark_md"
                }
            },
            {"tag": "hr"}
        ] + topic_items[:-1] # 移除最后一个 hr
        
        return await NotificationService.send_feishu_card(
            title="🌐 全球宏观热点扫描简报",
            content="每日宏观动态汇总",
            elements=elements,
            color="blue",
            msg_type="MACRO_SUMMARY",
            user_id=user_id,
            webhook_url=webhook_url
        )

    @staticmethod
    async def send_price_alert(ticker: str, name: str, current_price: float, target_price: float, is_stop_loss: bool = False, user_id: Optional[str] = None, webhook_url: Optional[str] = None):
        """
        发送价格触达预警：明确区分 🚀 止盈达成 或 ⚠️ 止损警戒
        支持根据 Ticker 自动识别币种 (USD/CNY)
        """
        # 币种识别逻辑
        is_us = not (ticker.isdigit() and len(ticker) == 6)
        currency = "USD" if is_us else "CNY"

        if is_stop_loss:
            color = "red"
            action_name = "止损警戒位"
            title_prefix = "⚠️ 触发止损警戒"
        else:
            color = "green"
            action_name = "止盈目标位"
            title_prefix = "🚀 达成止盈目标"
        
        elements = [
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {
                            "content": f"**证券代码**: {ticker}",
                            "tag": "lark_md"
                        }
                    },
                    {
                        "is_short": True,
                        "text": {
                            "content": f"**证券名称**: {name}",
                            "tag": "lark_md"
                        }
                    }
                ]
            },
            {
                "tag": "hr"
            },
            {
                "tag": "div",
                "text": {
                    "content": f"**当前市价**: {currency} {current_price}\n**目标建议 ({action_name})**: {currency} {target_price}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "建议操作：请及时关注账户状况，根据既定交易计划执行。"
                    }
                ]
            }
        ]
        
        return await NotificationService.send_feishu_card(
            title=f"{title_prefix}: {ticker}",
            content=f"{name} ({ticker}) 已触达{action_name}",
            elements=elements,
            color=color,
            msg_type="PRICE_ALERT",
            ticker=ticker,
            user_id=user_id,
            webhook_url=webhook_url
        )

    @staticmethod
    async def send_hourly_summary(summary_text: str, count: int, sentiment: str = "中性", email: str = "", user_id: Optional[str] = None, webhook_url: Optional[str] = None):
        """
        发送每小时财联社新闻精要总结
        """
        sentiment_icon = "📈" if "利好" in sentiment else "📉" if "利空" in sentiment else "⚖️"
        
        elements = [
            {
                "tag": "div",
                "text": {
                    "content": f"📊 **本小时快讯回顾**: 共计抓取 `{count}` 条实时资讯。\n市场情绪倾向: {sentiment_icon} **{sentiment}**",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "div",
                "text": {
                    "content": f"**AI 核心研判**:\n{summary_text}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": f"账号归属: {email}\n建议操作：请结合个股诊断功能进行深度分析。"
                    }
                ]
            }
        ]
        
        return await NotificationService.send_feishu_card(
            title="⏰ 财联社每小时新闻精要",
            content=summary_text,
            elements=elements,
            color="blue",
            msg_type="HOURLY_NEWS_SUMMARY",
            user_id=user_id,
            webhook_url=webhook_url
        )
