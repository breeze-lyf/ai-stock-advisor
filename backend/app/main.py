# 主程序入口 (Main Entry Point)
# 职责：初始化 FastAPI 应用、配置全局日志、添加中间件、挂载路由
import time
import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from app.core.config import settings
from app.core import security

# 1. 全局日志配置 (Global Logging Configuration)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("api_logger")

# 降低 SQLAlchemy 日志级别，减少噪音
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

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
        f"Unhandled exception on {request.method} {request.url.path}: "
        f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
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
        logger.error(f"Middleware caught unhandled error: {type(exc).__name__}: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    # 计算并格式化处理时间
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = f"{process_time:.2f}ms"
    
    logger.info(
        f"rid={request.scope.get('root_path') or ''}{request.url.path} "
        f"method={request.method} "
        f"status_code={response.status_code} "
        f"user_id={user_id} "
        f"time={formatted_process_time}"
    )
    
    response.headers["X-Process-Time"] = formatted_process_time
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


app.include_router(api_router, prefix="/api")

@app.get("/health", tags=["System"])
async def health_check():
    """健康检查接口：确保后端服务在线"""
    return {"status": "ok", "message": "Service is healthy"}

@app.get("/", include_in_schema=False)
async def root():
    """欢迎页面"""
    return {"message": "Welcome to AI Smart Investment Advisor API"}

