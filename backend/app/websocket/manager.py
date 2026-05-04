"""
WebSocket 实时推送服务
支持实时股价更新、AI 分析完成通知、预警触发等
"""
import asyncio
import json
import logging
import uuid
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timezone

from app.utils.time import utc_now_naive

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """WebSocket 连接管理器

    修复：集成 Redis Pub/Sub 支持多 worker 水平扩展。
    当用户连接到 worker A 时，worker B 发送的消息也能通过 Redis 路由到 worker A。
    """

    CHANNEL_PREFIX = "ws:"

    def __init__(self):
        # {user_id: {connection_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # 心跳配置
        self.heartbeat_timeout = 30
        self.heartbeat_interval = 10
        # 当前 worker 的唯一标识
        self.worker_id = str(uuid.uuid4())[:8]
        # Redis Pub/Sub 后台任务
        self._pubsub_task: asyncio.Task | None = None
        self._redis_client = None

    async def start(self):
        """启动 Redis Pub/Sub 监听（用于跨 worker 消息路由）。"""
        from app.core.redis_client import get_redis
        self._redis_client = await get_redis()
        if not self._redis_client:
            logger.info("[WebSocket] Redis unavailable — running in single-worker mode")
            return
        # 订阅全局 WebSocket 频道
        self._pubsub = self._redis_client.pubsub()
        await self._pubsub.subscribe(f"{self.CHANNEL_PREFIX}global")
        self._pubsub_task = asyncio.create_task(self._listen_pubsub())
        logger.info(f"[WebSocket] Redis Pub/Sub started (worker={self.worker_id})")

    async def stop(self):
        """停止 Redis Pub/Sub。"""
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()

    async def _listen_pubsub(self):
        """后台任务：监听 Redis Pub/Sub 消息并投递到本地连接。"""
        try:
            async for msg in self._pubsub.listen():
                if msg["type"] != "message":
                    continue
                try:
                    data = json.loads(msg["data"])
                except json.JSONDecodeError:
                    continue
                target_user_id = data.get("user_id")
                if target_user_id and target_user_id in self.active_connections:
                    message = data.get("message", {})
                    for conn_id, ws in list(self.active_connections[target_user_id].items()):
                        try:
                            await ws.send_json(message)
                        except Exception:
                            pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[WebSocket] Pub/Sub listener error: {e}")

    async def _publish_message(self, user_id: str, message: dict):
        """通过 Redis Pub/Sub 发布消息（所有 worker 都能收到）。"""
        if not self._redis_client:
            return
        try:
            await self._redis_client.publish(
                f"{self.CHANNEL_PREFIX}global",
                json.dumps({"user_id": user_id, "message": message}),
            )
        except Exception as e:
            logger.error(f"[WebSocket] Failed to publish message: {e}")

    async def connect(self, websocket: WebSocket, user_id: str, connection_id: str) -> bool:
        try:
            await websocket.accept()
            if user_id not in self.active_connections:
                self.active_connections[user_id] = {}
            self.active_connections[user_id][connection_id] = websocket
            logger.info(f"WebSocket connected: user={user_id}, connection={connection_id}")
            await self.send_personal_message(
                websocket,
                {
                    "type": "connection_established",
                    "data": {
                        "user_id": user_id,
                        "connection_id": connection_id,
                        "timestamp": utc_now_naive().isoformat(),
                    }
                }
            )
            return True
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False

    def disconnect(self, user_id: str, connection_id: str):
        if user_id in self.active_connections:
            if connection_id in self.active_connections[user_id]:
                del self.active_connections[user_id][connection_id]
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected: user={user_id}, connection={connection_id}")

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise

    async def send_to_user(self, user_id: str, message: dict):
        """向指定用户发送消息，通过 Redis Pub/Sub 广播到所有 worker。"""
        # 如果用户在本 worker 上有连接，直接发送
        if user_id in self.active_connections:
            failed = []
            for conn_id, ws in self.active_connections[user_id].items():
                try:
                    await ws.send_json(message)
                except Exception:
                    failed.append(conn_id)
            for conn_id in failed:
                self.disconnect(user_id, conn_id)
            return
        # 用户不在本 worker 上，通过 Redis 路由
        await self._publish_message(user_id, message)

    async def broadcast(self, message: dict):
        """广播消息给所有连接的用户（通过 Redis Pub/Sub）。"""
        await self._publish_message("__broadcast__", message)
        # 同时发送给本地连接
        for user_id in list(self.active_connections.keys()):
            try:
                await self.send_to_user(user_id, message)
            except Exception:
                pass

    async def broadcast_to_ticker_watchers(self, ticker: str, message: dict):
        await self.broadcast(message)

    async def send_heartbeat(self, user_id: str):
        await self.send_to_user(user_id, {
            "type": "heartbeat",
            "data": {"timestamp": utc_now_naive().isoformat()},
        })

    def get_connection_count(self) -> int:
        return sum(len(conns) for conns in self.active_connections.values())

    def get_user_connection_count(self, user_id: str) -> int:
        return len(self.active_connections.get(user_id, {}))


# 全局单例
websocket_manager = WebSocketConnectionManager()


class MessageType:
    CONNECTION_ESTABLISHED = "connection_established"
    HEARTBEAT = "heartbeat"
    PRICE_UPDATE = "price_update"
    ANALYSIS_COMPLETE = "analysis_complete"
    ALERT_TRIGGERED = "alert_triggered"
    SYSTEM_NOTIFICATION = "system_notification"


def create_message(message_type: str, data: dict) -> dict:
    return {
        "type": message_type,
        "data": data,
        "timestamp": utc_now_naive().isoformat(),
    }


async def notify_price_update(user_id: str, ticker: str, price: float, change_percent: float):
    await websocket_manager.send_to_user(user_id, create_message(
        MessageType.PRICE_UPDATE,
        {"ticker": ticker, "price": price, "change_percent": change_percent},
    ))


async def notify_analysis_complete(user_id: str, ticker: str, analysis_id: str):
    await websocket_manager.send_to_user(user_id, create_message(
        MessageType.ANALYSIS_COMPLETE,
        {"ticker": ticker, "analysis_id": analysis_id, "message": f"{ticker} 的 AI 分析已完成"},
    ))


async def notify_alert_triggered(user_id: str, alert_type: str, ticker: str, message: str):
    await websocket_manager.send_to_user(user_id, create_message(
        MessageType.ALERT_TRIGGERED,
        {"alert_type": alert_type, "ticker": ticker, "message": message},
    ))
