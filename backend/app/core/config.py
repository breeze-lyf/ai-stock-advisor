from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Smart Investment Advisor"
    DATABASE_URL: str = "sqlite+aiosqlite:///./ai_advisor.db"
    
    # Security
    SECRET_KEY: str = "dev_secret_key_change_me_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALLOWED_ORIGINS: list[str] = []
    
    # Encryption for API Keys (32 byte base64 encoded string)
    ENCRYPTION_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    SILICONFLOW_API_KEY: Optional[str] = None
    DASHSCOPE_API_KEY: Optional[str] = None
    DASHSCOPE_BASE_URL: Optional[str] = None
    DEFAULT_AI_MODEL: str = "qwen3.5-plus"
    TAVILY_API_KEY: Optional[str] = None
    HTTP_PROXY: Optional[str] = None
    HTTPS_PROXY: Optional[str] = None
    NO_PROXY: Optional[str] = None
    AKSHARE_BYPASS_PROXY: bool = True
    AUTO_DISABLE_UNAVAILABLE_PROXY: bool = True
    FEISHU_WEBHOOK_URL: Optional[str] = None
    FEISHU_SECRET: Optional[str] = None

    # IBKR TWS/IB Gateway 连接配置
    IBKR_HOST: str = "127.0.0.1"       # TWS/Gateway 监听地址
    IBKR_PORT: int = 7497              # 默认 Paper Trading 端口 (Live=7496, Gateway Live=4001, Gateway Paper=4002)
    IBKR_CLIENT_ID: int = 10           # 客户端 ID，避免与交易终端冲突
    IBKR_ENABLED: bool = False         # 总开关：设为 True 以启用 IBKR 数据源

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
