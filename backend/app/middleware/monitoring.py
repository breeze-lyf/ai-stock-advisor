"""
API 监控中间件
采集 API 响应时间、错误率等指标
"""
import logging
import time
import asyncio
import json
from typing import Callable, Awaitable, Deque
from collections import deque
from dataclasses import dataclass
from fastapi import Request, Response
from datetime import datetime, date

logger = logging.getLogger(__name__)


@dataclass
class MetricRecord:
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    request_date: date
    request_hour: int


class APIMonitorMiddleware:
    """API 监控中间件

    使用内存缓冲 + 定期批量写入，避免每个请求都创建数据库连接。
    """

    # 全局缓冲：所有请求共享一个队列
    _buffer: Deque[MetricRecord] = deque()
    _flush_task: asyncio.Task | None = None
    _flush_interval: float = 10.0  # 每 10 秒或攒够 100 条时批量写入
    _batch_size: int = 100

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        await self._enqueue_metrics(request, response, process_time)
        response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
        return response

    async def _enqueue_metrics(self, request: Request, response: Response, process_time: float):
        path = request.url.path
        if path.startswith(("/static", "/favicon", "/health", "/metrics")):
            return

        now = datetime.now()
        record = MetricRecord(
            endpoint=self._get_route(request),
            method=request.method,
            status_code=response.status_code,
            response_time_ms=round(process_time * 1000, 2),
            request_date=now.date(),
            request_hour=now.hour,
        )
        self._buffer.append(record)

        # 慢查询告警仍即时输出
        if process_time > 1.0:
            logger.warning(f"Slow request: {request.method} {record.endpoint} - {record.response_time_ms}ms")

        # 启动批量刷新任务（仅一次）
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._periodic_flush())

    async def _periodic_flush(self):
        """定期将缓冲中的指标批量写入数据库。"""
        from app.core.database import SessionLocal
        from app.models.monitoring import APIMetric

        while True:
            await asyncio.sleep(self._flush_interval)

            if not self._buffer:
                continue

            # 取出当前批次
            batch: list[MetricRecord] = []
            while self._buffer and len(batch) < self._batch_size:
                batch.append(self._buffer.popleft())

            if not batch:
                continue

            try:
                async with SessionLocal() as db:
                    metrics = [
                        APIMetric(
                            endpoint=r.endpoint,
                            method=r.method,
                            status_code=r.status_code,
                            response_time_ms=r.response_time_ms,
                            request_date=r.request_date,
                            request_hour=r.request_hour,
                        )
                        for r in batch
                    ]
                    db.add_all(metrics)
                    await db.commit()
            except Exception as e:
                logger.error(f"Failed to batch-write API metrics: {e}")

    def _get_route(self, request: Request) -> str:
        """获取规范化路由路径（将数字/UUID 替换为 :id，将股票代码替换为 :ticker）。"""
        parts = request.url.path.strip("/").split("/")
        normalized = []
        for i, part in enumerate(parts):
            if part.isdigit() or (len(part) == 36 and part.count("-") == 4):
                normalized.append(":id")
            # 简单启发：在 /stocks/ 或 /analysis/ 后出现的字母数字组合视为 ticker
            elif i > 0 and parts[i - 1] in ("stocks", "analysis", "portfolio") and part.replace(".", "").replace("-", "").isalnum():
                normalized.append(":ticker")
            else:
                normalized.append(part)
        return "/" + "/".join(normalized)


class ErrorTrackerMiddleware:
    """错误追踪中间件 — 记录未处理异常到数据库。"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            await self._record_error(request, e)
            raise

    async def _record_error(self, request: Request, error: Exception):
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
