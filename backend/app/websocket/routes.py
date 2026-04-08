"""
WebSocket 路由端点
处理 WebSocket 连接、心跳、消息收发
"""
import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core import security
from app.websocket.manager import (
    websocket_manager,
    create_message,
    MessageType,
    notify_analysis_complete,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT Token"),
    connection_id: Optional[str] = Query(None, description="Connection ID"),
):
    """
    WebSocket 连接端点

    查询参数:
    - token: JWT 访问令牌
    - connection_id: 连接 ID（可选，用于区分同一用户的多个连接）

    消息格式:
    {
        "type": "message_type",
        "data": {...}
    }

    支持的消息类型:
    - ping: 客户端发送心跳
    - subscribe_ticker: 订阅指定股票的实时价格
    - unsubscribe_ticker: 取消订阅
    """
    # 验证 token
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    try:
        payload = security.decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4002, reason="Invalid token")
            return
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        await websocket.close(code=4003, reason="Token validation failed")
        return

    # 生成连接 ID
    if not connection_id:
        import uuid
        connection_id = str(uuid.uuid4())

    # 建立连接
    connected = await websocket_manager.connect(websocket, user_id, connection_id)
    if not connected:
        return

    # 启动心跳任务
    heartbeat_task = asyncio.create_task(
        heartbeat_loop(websocket, user_id, connection_id)
    )

    try:
        while True:
            # 等待客户端消息
            try:
                data = await websocket.receive_json()
                await handle_message(websocket, user_id, connection_id, data)
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: user={user_id}, connection={connection_id}")
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"}
                })
    finally:
        # 清理连接
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        websocket_manager.disconnect(user_id, connection_id)


async def heartbeat_loop(websocket: WebSocket, user_id: str, connection_id: str):
    """心跳循环"""
    while True:
        try:
            await asyncio.sleep(30)  # 30 秒发送一次心跳
            await websocket.send_json({
                "type": "heartbeat",
                "data": {"timestamp": asyncio.get_event_loop().time()}
            })
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
            break


async def handle_message(websocket: WebSocket, user_id: str, connection_id: str, data: dict):
    """
    处理客户端消息

    支持的消息类型:
    - ping: 心跳响应
    - subscribe_ticker: 订阅股票
    - unsubscribe_ticker: 取消订阅
    - get_connection_info: 获取连接信息
    """
    message_type = data.get("type")

    if message_type == "ping":
        # 心跳响应
        await websocket.send_json({
            "type": "pong",
            "data": {"timestamp": data.get("timestamp")}
        })

    elif message_type == "subscribe_ticker":
        ticker = data.get("data", {}).get("ticker")
        if ticker:
            logger.info(f"User {user_id} subscribed to {ticker}")
            # TODO: 实现股票订阅逻辑

    elif message_type == "unsubscribe_ticker":
        ticker = data.get("data", {}).get("ticker")
        if ticker:
            logger.info(f"User {user_id} unsubscribed from {ticker}")
            # TODO: 实现取消订阅逻辑

    elif message_type == "get_connection_info":
        await websocket.send_json({
            "type": "connection_info",
            "data": {
                "user_id": user_id,
                "connection_id": connection_id,
                "active_connections": websocket_manager.get_user_connection_count(user_id),
                "total_connections": websocket_manager.get_connection_count(),
            }
        })

    else:
        await websocket.send_json({
            "type": "error",
            "data": {"message": f"Unknown message type: {message_type}"}
        })


# 辅助函数：从 main.py 调用
async def notify_user_analysis_complete(user_id: str, ticker: str):
    """通知用户 AI 分析完成"""
    await notify_analysis_complete(user_id, ticker, f"analysis_{ticker}")
