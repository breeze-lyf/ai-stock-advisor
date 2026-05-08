# 主程序入口 (Main Entry Point)
# 职责：组装 FastAPI 应用、注册中间件、挂载路由、暴露健康检查
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.lifespan import lifespan
from app.core.middleware import (
    register_exception_handlers,
    register_request_logging_middleware,
    setup_cors,
)
from app.core.rate_limiter import limiter

# Prometheus metrics instrumentation
try:
    from prometheus_fastapi_instrumentator import Instrumentator as _Instrumentator
    _prometheus_available = True
except ImportError:
    _prometheus_available = False

# 全局日志配置 — 在 lifespan 导入时也会引用同一 logger
from app.utils.json_logger import setup_logging
log_format = os.getenv("LOG_FORMAT", "json")
log_level = os.getenv("LOG_LEVEL", "INFO")
environment = os.getenv("ENVIRONMENT", "development")
setup_logging(
    log_format=log_format,
    log_level=log_level,
    service_name="ai-stock-advisor",
    environment=environment,
    log_file=".local/runtime-logs/app.log"
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI 智能投资助手后端 API，集成多源数据与 LLM 分析能力",
    version="1.0.0",
    lifespan=lifespan,
)

# 速率限制异常处理
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 全局异常处理器
register_exception_handlers(app)

# 请求日志中间件
register_request_logging_middleware(app)

# CORS
setup_cors(app)

# 路由挂载
from app.api.v1.api import api_router
app.include_router(api_router, prefix="/api/v1")

# WebSocket 路由（不经过 API 前缀）
from app.websocket.routes import router as websocket_router
app.include_router(websocket_router)

# Prometheus 指标暴露
if _prometheus_available:
    _Instrumentator(
        should_group_status_codes=True,
        excluded_handlers=["/health", "/readiness", "/metrics"],
    ).instrument(app).expose(app, include_in_schema=False, tags=["System"])


@app.get("/health", tags=["System"])
async def health_check():
    """健康检查接口：确保后端服务在线"""
    return {"status": "ok", "message": "Service is healthy"}


@app.get("/health/yfinance", tags=["System"])
async def yfinance_health_check():
    """Yahoo Finance 连接健康检查接口（通过 mihomo 代理走海外节点）"""
    return {"status": "ok", "proxy": "mihomo"}


@app.get("/readiness", tags=["System"])
async def readiness_check():
    """就绪检查接口：验证数据库和 Redis 连接正常后才对外提供服务"""
    from sqlalchemy import text
    from app.core.database import SessionLocal
    from app.core.redis_client import get_redis

    checks: dict[str, str] = {}

    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        from app.core.lifespan import logger as lifespan_logger
        lifespan_logger.error(f"Readiness DB check failed: {exc}")
        checks["database"] = "error"

    try:
        redis = await get_redis()
        if redis:
            await redis.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "unavailable"
    except Exception as exc:
        from app.core.lifespan import logger as lifespan_logger
        lifespan_logger.warning(f"Readiness Redis check failed: {exc}")
        checks["redis"] = "error"

    all_critical_ok = checks.get("database") == "ok"
    status_code = 200 if all_critical_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if all_critical_ok else "not_ready", "checks": checks},
    )


@app.get("/", include_in_schema=False)
async def root():
    """欢迎页面"""
    return {"message": "Welcome to AI Smart Investment Advisor API"}
