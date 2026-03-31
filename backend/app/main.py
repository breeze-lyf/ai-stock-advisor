# 主程序入口 (Main Entry Point)
# 职责：初始化 FastAPI 应用、配置全局日志、添加中间件、挂载路由
import time
import logging
import traceback
import os
import socket
import asyncio
from contextlib import asynccontextmanager
from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core import security
from app.core.rate_limiter import limiter
from app.utils.json_logger import setup_logging

# Prometheus metrics instrumentation
try:
    from prometheus_fastapi_instrumentator import Instrumentator as _Instrumentator
    _prometheus_available = True
except ImportError:
    _prometheus_available = False

# 全局速率限制器实例由 app/core/rate_limiter.py 统一管理

# 1. 全局日志配置 (Global Logging Configuration)
# 支持JSON格式日志，便于Loki聚合分析
log_format = os.getenv("LOG_FORMAT", "json")
log_level = os.getenv("LOG_LEVEL", "INFO")
environment = os.getenv("ENVIRONMENT", "production")

logger = setup_logging(
    log_format=log_format,
    log_level=log_level,
    service_name="ai-stock-advisor",
    environment=environment,
    log_file=".local/runtime-logs/app.log"
)

def _patch_py_mini_racer_cleanup_bug() -> None:
    """
    兼容补丁：py_mini_racer 在 Python 3.14 下可能在解释器回收期触发 __del__ 空指针。
    该异常不影响业务，但会污染日志，这里做安全析构兜底。
    """
    try:
        from py_mini_racer.py_mini_racer import MiniRacer
    except Exception:
        return

    if getattr(MiniRacer, "_safe_del_patched", False):
        return

    def _safe_del(self):
        try:
            ext = getattr(self, "ext", None)
            if ext is None:
                return
            free_ctx = getattr(ext, "mr_free_context", None)
            if callable(free_ctx):
                free_ctx(getattr(self, "ctx", None))
        except Exception:
            # 析构阶段静默处理，避免退出时噪声
            pass

    MiniRacer.__del__ = _safe_del  # type: ignore[method-assign]
    MiniRacer._safe_del_patched = True  # type: ignore[attr-defined]


def _patch_httpx_asyncclient_compat() -> None:
    """
    兼容补丁：部分第三方 SDK 仍依赖旧版 httpx AsyncClient 行为：
    - AsyncClient(..., proxies=...) 参数
    - client._limits 内部属性
    在 httpx 0.28+ 中这两处可能不兼容，这里做最小兼容兜底。
    """
    try:
        import inspect
        import httpx
    except Exception:
        return

    async_client_cls = httpx.AsyncClient
    if getattr(async_client_cls, "_compat_init_patched", False):
        return

    original_init = async_client_cls.__init__
    accepts_proxies = "proxies" in inspect.signature(original_init).parameters

    def _compat_init(self, *args, **kwargs):
        if "proxies" in kwargs and "proxy" not in kwargs and not accepts_proxies:
            raw_proxies = kwargs.pop("proxies")
            if isinstance(raw_proxies, dict):
                proxy_val = (
                    raw_proxies.get("https://")
                    or raw_proxies.get("http://")
                    or raw_proxies.get("https")
                    or raw_proxies.get("http")
                )
            else:
                proxy_val = raw_proxies
            kwargs["proxy"] = proxy_val
        limits = kwargs.get("limits")
        original_init(self, *args, **kwargs)
        if not hasattr(self, "_limits"):
            # 兼容旧 SDK 读取 client._limits 的行为
            self._limits = limits

    async_client_cls.__init__ = _compat_init  # type: ignore[method-assign]
    async_client_cls._compat_init_patched = True  # type: ignore[attr-defined]


def _is_proxy_reachable(proxy_url: str, timeout: float = 0.4) -> bool:
    try:
        parsed = urlparse(proxy_url)
        host = parsed.hostname
        port = parsed.port
        if not host or not port:
            return False
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _normalize_proxy_env() -> None:
    """
    启动时检查代理连通性：
    - 代理可达：保留配置
    - 代理不可达：自动清理当前进程代理环境变量，避免请求被卡死
    """
    http_proxy = getattr(settings, "HTTP_PROXY", None)
    https_proxy = getattr(settings, "HTTPS_PROXY", None) or http_proxy
    no_proxy = getattr(settings, "NO_PROXY", None)

    # 确保 .env 中的代理配置显式注入进程环境变量，供 requests/httpx 下游库读取
    if http_proxy:
        os.environ.setdefault("HTTP_PROXY", http_proxy)
        os.environ.setdefault("http_proxy", http_proxy)
    if https_proxy:
        os.environ.setdefault("HTTPS_PROXY", https_proxy)
        os.environ.setdefault("https_proxy", https_proxy)
    if no_proxy:
        os.environ.setdefault("NO_PROXY", no_proxy)
        os.environ.setdefault("no_proxy", no_proxy)

    if not getattr(settings, "AUTO_DISABLE_UNAVAILABLE_PROXY", True):
        return

    candidates = [p for p in [http_proxy, https_proxy] if p]
    if not candidates:
        return

    if any(_is_proxy_reachable(proxy) for proxy in candidates):
        logger.info("Proxy detected and reachable. Keeping proxy settings.")
        return

    for var in [
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
        "http_proxy", "https_proxy", "all_proxy",
        "NO_PROXY", "no_proxy"
    ]:
        os.environ.pop(var, None)
    logger.warning("Configured proxy is unreachable. Cleared proxy env vars for this process.")


# 尽早应用兼容补丁，覆盖可能在 startup 前初始化的第三方客户端。
_patch_httpx_asyncclient_compat()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _patch_py_mini_racer_cleanup_bug()
    _patch_httpx_asyncclient_compat()
    _normalize_proxy_env()

    from app.core.database import SessionLocal
    from app.services.system_ai_registry import ensure_system_ai_registry
    from app.services.scheduler import start_scheduler

    async with SessionLocal() as db:
        await ensure_system_ai_registry(db)

    scheduler_task = asyncio.create_task(start_scheduler())
    app.state.scheduler_task = scheduler_task
    logger.info("PHASE: Background scheduler task launched & DB synced.")

    try:
        yield
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            logger.info("PHASE: Background scheduler task cancelled.")
        from app.core.redis_client import close_redis
        await close_redis()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI 智能投资助手后端 API，集成多源数据与 LLM 分析能力",
    version="1.0.0",
    lifespan=lifespan,
)

# 速率限制异常处理
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 2. 全局异常处理器 (Global Exception Handler)
# 捕获所有未处理的异常，返回通用错误信息（不暴露内部细节）
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
    # Return a generic message — never expose exception type or details to clients
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# 3. HTTP 请求拦截中间件 (Custom Logging Middleware)
# 职责：记录请求耗时、请求路径、访问方法及当前操作的用户 ID
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # 尝试从 Authorization Header 中解析 JWT 以提取用户 ID
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
        # 中间件层兜底：即使 call_next 抛出异常也不会让 worker 崩溃
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
    
    # 计算并格式化处理时间
    duration_ms = (time.time() - start_time) * 1000
    
    # 结构化日志记录
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

# 4. 跨域资源共享配置 (CORS Configuration)
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

# 5. 路由挂载 (Router Inclusion)
from app.api.v1.api import api_router


app.include_router(api_router, prefix="/api/v1")

# Prometheus 指标暴露（若依赖包已安装）
if _prometheus_available:
    _Instrumentator(
        should_group_status_codes=True,
        excluded_handlers=["/health", "/readiness", "/metrics"],
    ).instrument(app).expose(app, include_in_schema=False, tags=["System"])

@app.get("/health", tags=["System"])
async def health_check():
    """健康检查接口：确保后端服务在线"""
    return {"status": "ok", "message": "Service is healthy"}

@app.get("/readiness", tags=["System"])
async def readiness_check():
    """就绪检查接口：验证数据库和 Redis 连接正常后才对外提供服务"""
    from sqlalchemy import text
    from app.core.database import SessionLocal
    from app.core.redis_client import get_redis

    checks: dict[str, str] = {}

    # Check database connectivity
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        logger.error(f"Readiness DB check failed: {exc}")
        checks["database"] = "error"

    # Check Redis connectivity (optional — degrades gracefully)
    try:
        redis = await get_redis()
        if redis:
            await redis.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "unavailable"
    except Exception as exc:
        logger.warning(f"Readiness Redis check failed: {exc}")
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
