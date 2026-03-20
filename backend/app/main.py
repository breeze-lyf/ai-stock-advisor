# 主程序入口 (Main Entry Point)
# 职责：初始化 FastAPI 应用、配置全局日志、添加中间件、挂载路由
import time
import logging
import traceback
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from app.core.config import settings
from app.core import security
from app.utils.json_logger import setup_logging

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
    log_file="app.log"
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI 智能投资助手后端 API，集成多源数据与 LLM 分析能力",
    version="1.0.0"
)

# 2. 全局异常处理器 (Global Exception Handler)
# 捕获所有未处理的异常，返回结构化错误信息而不是让 worker 崩溃
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
        content={
            "detail": f"Internal server error: {type(exc).__name__}",
            "message": str(exc)[:200]  # 截断避免泄露过多内部信息
        }
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

# 6. 后端后台任务启动 (Background Task Startup)
@app.on_event("startup")
async def startup_event():
    # 自动创建缺失的数据库表 (包括 notification_logs)
    from app.core.database import engine, Base, SessionLocal
    from app.models.notification import NotificationLog
    from app.services.system_ai_registry import ensure_system_ai_registry
    # 数据库同步现已通过 entrypoint.sh 中的 alembic upgrade head 统一处理

    async with SessionLocal() as db:
        await ensure_system_ai_registry(db)
    
    from app.services.scheduler import start_scheduler
    import asyncio
    # 使用 create_task 将调度循环挂在后台，不阻塞 Uvicorn 主进程启动
    asyncio.create_task(start_scheduler())
    logger.info("PHASE: Background scheduler task launched & DB synced.")

@app.get("/health", tags=["System"])
async def health_check():
    """健康检查接口：确保后端服务在线"""
    return {"status": "ok", "message": "Service is healthy"}

@app.get("/", include_in_schema=False)
async def root():
    """欢迎页面"""
    return {"message": "Welcome to AI Smart Investment Advisor API"}
