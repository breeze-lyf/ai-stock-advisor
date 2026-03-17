import asyncio
import logging

from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class MacroNotifier:
    """
    【宏观通知器 (Macro Notifier)】
    负责将 AI 分析后的宏观结论推送到客户端（如飞书 Webhook）。
    支持两种推送模式：
    1. 紧急雷达：针对热度极高（>=90）的单一重大事件。
    2. 宏观精要：每日/定期的全局主题汇总。
    """
    @staticmethod
    async def notify_topics(users, topics):
        """
        通知分发逻辑：
        - 遍历所有注册用户。
        - 根据主题热度决定是否发送紧急警报。
        """
        if not topics:
            return

        for user in users:
            # 1. 紧急警报扫描
            for topic in topics:
                # 热度阈值控制：只有 90 分以上的主题才触发独立推送
                if topic.heat_score >= 90:
                    try:
                        # 开启异步任务发送，避免一个用户失败影响后续用户
                        asyncio.create_task(
                            NotificationService.send_macro_alert(
                                title=topic.title,
                                summary=topic.summary,
                                heat_score=topic.heat_score,
                                user_id=user.id,
                                webhook_url=user.feishu_webhook_url,
                            )
                        )
                    except Exception as exc:
                        logger.error(f"Failed to trigger macro alert for user {user.email}: {exc}")

            # 2. 常规精要汇总推送
            try:
                asyncio.create_task(
                    NotificationService.send_macro_summary(
                        topics_count=len(topics),
                        topics_list=topics,
                        user_id=user.id,
                        webhook_url=user.feishu_webhook_url,
                    )
                )
            except Exception as exc:
                logger.error(f"Failed to trigger macro summary for user {user.email}: {exc}")
