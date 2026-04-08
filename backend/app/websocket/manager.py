"""
WebSocket 实时推送服务
支持实时股价更新、AI 分析完成通知、预警触发等
"""
import logging
import json
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """
    WebSocket 连接管理器

    功能：
    - 管理所有活跃的 WebSocket 连接
    - 支持按用户 ID 发送消息
    - 支持广播消息
    - 心跳检测
    - 断线重连处理
    """

    def __init__(self):
        # {user_id: {connection_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # 心跳配置
        self.heartbeat_timeout = 30  # 30 秒无心跳则断开
        self.heartbeat_interval = 10  # 10 秒发送一次心跳

    async def connect(self, websocket: WebSocket, user_id: str, connection_id: str) -> bool:
        """
        接受 WebSocket 连接

        Args:
            websocket: WebSocket 连接对象
            user_id: 用户 ID
            connection_id: 连接 ID（用于区分同一用户的多个连接）

        Returns:
            bool: 连接是否成功
        """
        try:
            await websocket.accept()

            if user_id not in self.active_connections:
                self.active_connections[user_id] = {}

            self.active_connections[user_id][connection_id] = websocket

            logger.info(f"WebSocket connected: user={user_id}, connection={connection_id}")

            # 发送欢迎消息
            await self.send_personal_message(
                websocket,
                {
                    "type": "connection_established",
                    "data": {
                        "user_id": user_id,
                        "connection_id": connection_id,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                }
            )

            return True
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False

    def disconnect(self, user_id: str, connection_id: str):
        """断开 WebSocket 连接"""
        if user_id in self.active_connections:
            if connection_id in self.active_connections[user_id]:
                del self.active_connections[user_id][connection_id]

            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        logger.info(f"WebSocket disconnected: user={user_id}, connection={connection_id}")

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """发送个人消息"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise

    async def send_to_user(self, user_id: str, message: dict):
        """
        向指定用户发送消息（所有活跃连接）

        Args:
            user_id: 用户 ID
            message: 消息字典
        """
        if user_id not in self.active_connections:
            return

        failed_connections = []
        for connection_id, websocket in self.active_connections[user_id].items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to connection {connection_id}: {e}")
                failed_connections.append(connection_id)

        # 清理失败的连接
        for connection_id in failed_connections:
            self.disconnect(user_id, connection_id)

    async def broadcast(self, message: dict):
        """广播消息给所有连接的用户"""
        failed_users = []
        for user_id in list(self.active_connections.keys()):
            try:
                await self.send_to_user(user_id, message)
            except Exception as e:
                logger.error(f"Failed to broadcast to user {user_id}: {e}")
                failed_users.append(user_id)

    async def broadcast_to_ticker_watchers(self, ticker: str, message: dict):
        """
        向关注指定股票的所有用户发送消息

        Args:
            ticker: 股票代码
            message: 消息字典
        """
        # 这里可以扩展为维护一个 ticker -> user_ids 的映射
        # 目前先广播给所有用户
        await self.broadcast(message)

    async def send_heartbeat(self, user_id: str):
        """发送心跳消息"""
        await self.send_to_user(user_id, {
            "type": "heartbeat",
            "data": {
                "timestamp": datetime.utcnow().isoformat(),
            }
        })

    def get_connection_count(self) -> int:
        """获取活跃连接总数"""
        return sum(len(connections) for connections in self.active_connections.values())

    def get_user_connection_count(self, user_id: str) -> int:
        """获取指定用户的连接数"""
        return len(self.active_connections.get(user_id, {}))


# 全局单例
websocket_manager = WebSocketConnectionManager()


# 消息类型定义
class MessageType:
    """WebSocket 消息类型"""
    CONNECTION_ESTABLISHED = "connection_established"
    HEARTBEAT = "heartbeat"
    PRICE_UPDATE = "price_update"
    ANALYSIS_COMPLETE = "analysis_complete"
    ALERT_TRIGGERED = "alert_triggered"
    SYSTEM_NOTIFICATION = "system_notification"


# 消息工厂
def create_message(message_type: str, data: dict) -> dict:
    """创建标准格式的消息"""
    return {
        "type": message_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }


# 便捷函数
async def notify_price_update(user_id: str, ticker: str, price: float, change_percent: float):
    """通知股价更新"""
    await websocket_manager.send_to_user(user_id, create_message(
        MessageType.PRICE_UPDATE,
        {
            "ticker": ticker,
            "price": price,
            "change_percent": change_percent,
        }
    ))


async def notify_analysis_complete(user_id: str, ticker: str, analysis_id: str):
    """通知 AI 分析完成"""
    await websocket_manager.send_to_user(user_id, create_message(
        MessageType.ANALYSIS_COMPLETE,
        {
            "ticker": ticker,
            "analysis_id": analysis_id,
            "message": f"{ticker} 的 AI 分析已完成",
        }
    ))


async def notify_alert_triggered(user_id: str, alert_type: str, ticker: str, message: str):
    """通知预警触发"""
    await websocket_manager.send_to_user(user_id, create_message(
        MessageType.ALERT_TRIGGERED,
        {
            "alert_type": alert_type,
            "ticker": ticker,
            "message": message,
        }
    ))
