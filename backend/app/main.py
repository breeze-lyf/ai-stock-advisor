import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from app.core.config import settings
from app.core import security

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("api_logger")

app = FastAPI(title="AI Smart Investment Advisor")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Try to get user_id from JWT token in Authorization header
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

    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = f"{process_time:.2f}ms"
    
    logger.info(
        f"rid={request.scope.get('root_path')}{request.url.path} "
        f"method={request.method} "
        f"status_code={response.status_code} "
        f"user_id={user_id} "
        f"time={formatted_process_time}"
    )
    
    response.headers["X-Process-Time"] = formatted_process_time
    return response

# CORS
# In production, this should be specific.
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

# 允许从环境变量中添加更多域名（如生产环境域名）
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

from app.api import portfolio, analysis, auth, user

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Service is healthy"}

@app.get("/")
async def root():
    return {"message": "Welcome to AI Smart Investment Advisor API"}
