"""
Middleware: exception handlers, request logging, CORS, rate limit errors.
"""
import logging
import time
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import jwt

from app.core import security
from app.core.config import settings

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。"""

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {exc}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "error_type": type(exc).__name__,
                "stack_trace": traceback.format_exc()
            }
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


def register_request_logging_middleware(app: FastAPI) -> None:
    """注册 HTTP 请求拦截中间件：记录耗时、路径、用户 ID。"""

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()

        user_id = "anonymous"
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(
                    token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
                )
                user_id = payload.get("sub", "anonymous")
            except Exception:
                user_id = "invalid_token"

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Middleware caught unhandled error: {type(exc).__name__}: {exc}",
                extra={
                    "user_id": user_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "error_type": type(exc).__name__,
                    "stack_trace": traceback.format_exc()
                }
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )

        duration_ms = (time.time() - start_time) * 1000

        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "user_id": user_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2)
            }
        )

        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"
        return response


def setup_cors(app: FastAPI) -> None:
    """配置跨域资源共享 (CORS)。"""
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://47.100.109.73",
        "http://47.100.109.73:3000",
    ]

    env_origins = settings.ALLOWED_ORIGINS if hasattr(settings, "ALLOWED_ORIGINS") else []
    if env_origins:
        origins.extend(env_origins)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
