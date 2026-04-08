"""
API 监控中间件
采集 API 响应时间、错误率等指标
"""
import logging
import time
import json
from typing import Callable, Awaitable
from fastapi import Request, Response
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import insert

logger = logging.getLogger(__name__)


class APIMonitorMiddleware:
    """
    API 监控中间件

    功能：
    1. 记录每个 API 请求的响应时间
    2. 统计错误率
    3. 记录慢查询
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        start_time = time.time()

        # 处理请求
        response = await call_next(request)

        # 计算响应时间
        process_time = time.time() - start_time

        # 记录指标
        await self._record_metrics(request, response, process_time)

        # 添加响应头
        response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))  # ms

        return response

    async def _record_metrics(self, request: Request, response: Response, process_time: float):
        """记录 API 指标到数据库"""
        from app.core.database import SessionLocal
        from app.models.monitoring import APIMetric

        # 跳过静态文件和监控端点
        path = request.url.path
        if path.startswith(("/static", "/favicon", "/health", "/metrics")):
            return

        status_code = response.status_code
        method = request.method
        route = self._get_route(request)

        try:
            async with SessionLocal() as db:
                # 记录 API 指标
                metric = APIMetric(
                    endpoint=route,
                    method=method,
                    status_code=status_code,
                    response_time_ms=round(process_time * 1000, 2),
                    request_date=date.today(),
                )
                db.add(metric)
                await db.commit()

                # 记录慢查询（>1000ms）
                if process_time > 1.0:
                    logger.warning(
                        f"Slow request: {method} {route} - {round(process_time * 1000, 2)}ms"
                    )

        except Exception as e:
            logger.error(f"Failed to record API metric: {e}")

    def _get_route(self, request: Request) -> str:
        """获取路由路径"""
        route = request.url.path
        # 替换路径中的 ID 部分
        parts = route.strip("/").split("/")
        normalized_parts = []
        for part in parts:
            # 如果是数字或 UUID，替换为 :id
            if part.isdigit() or (len(part) == 36 and part.count("-") == 4):
                normalized_parts.append(":id")
            else:
                normalized_parts.append(part)
        return "/" + "/".join(normalized_parts)


class ErrorTrackerMiddleware:
    """
    错误追踪中间件
    记录所有未处理的异常
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            await self._record_error(request, e)
            raise

    async def _record_error(self, request: Request, error: Exception):
        """记录错误到数据库"""
        from app.core.database import SessionLocal
        from app.models.monitoring import ErrorLog

        try:
            async with SessionLocal() as db:
                error_log = ErrorLog(
                    endpoint=request.url.path,
                    method=request.method,
                    error_type=type(error).__name__,
                    error_message=str(error),
                    status_code=500,
                )
                db.add(error_log)
                await db.commit()

                logger.error(f"Error on {request.method} {request.url.path}: {error}")

        except Exception as e:
            logger.error(f"Failed to record error log: {e}")
