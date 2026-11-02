from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "AI Smart Investment Advisor"
    DATABASE_URL: str  # Required — must be set in .env (e.g., postgresql+asyncpg://...)
    
    # Security
    SECRET_KEY: str  # Required — no default. Must be set in .env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: list[str] = []

    # Data retention: analysis reports older than this many days are purged nightly
    DATA_RETENTION_DAYS: int = 90

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        insecure_defaults = {
            "dev_secret_key_change_me_in_production",
            "secret",
            "changeme",
        }
        if v.lower() in insecure_defaults or len(v) < 32:
            raise ValueError(
                "SECRET_KEY is insecure. Set a random value (>= 32 chars) in .env. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v

    # Encryption for API Keys (Fernet 32-byte base64-encoded key)
    ENCRYPTION_KEY: Optional[str] = None

    # Redis (optional — used for caching and distributed locks)
    REDIS_URL: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    SILICONFLOW_API_KEY: Optional[str] = None
    DASHSCOPE_API_KEY: Optional[str] = None
    DASHSCOPE_BASE_URL: Optional[str] = None
    DEFAULT_AI_MODEL: str = "qwen3.5-plus"

    # Agent (P1) — system-default OpenAI-compatible relay (e.g. 致拓 relay).
    # Used when the user has no BYOK model/credential. Leave empty to fall back
    # to the existing provider_configs routing.
    LLM_BASE_URL: Optional[str] = None
    LLM_MODEL: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    AGENT_MAX_STEPS: int = 8
    AGENT_LLM_TIMEOUT_SECONDS: int = 90
    AGENT_TOOL_TIMEOUT_SECONDS: int = 60
    AGENT_TOOL_RESULT_MAX_CHARS: int = 6000
    # Agent P2
    AGENT_BRIEF_ENABLED: bool = False        # 每日简报定时任务（默认关闭）
    AGENT_BRIEF_HOUR: int = 8                # 北京时间几点生成（整点后 15 分钟窗口内）
    AGENT_BRIEF_MAX_USERS: int = 200
    AGENT_ADVICE_REVIEW_ENABLED: bool = True  # 建议到期复盘（每日一次，只读行情）
    AGENT_TRIAL_ENABLED: bool = True         # 免登录试用 /try
    AGENT_TRIAL_DAILY_LIMIT: int = 5         # 每 IP 每天提问次数
    AGENT_TRIAL_MAX_STEPS: int = 4
    FEATURE_BILLING_ENABLED: bool = False    # 订阅/计费相关 UI（前端另有 NEXT_PUBLIC_FEATURE_BILLING）
    # DEPRECATED: TAVILY_API_KEY is intentionally NOT used as a system-level fallback.
    # News search via Tavily is a user-optional feature only — the key must be configured
    # per-user in Settings → Provider Credentials. Setting this env var has no effect.
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

    # 市场环境标识：用于数据源智能路由
    # True = 服务器环境（如阿里云，无代理，AkShare 更可靠）
    # False = 本地环境（有代理，YFinance 美股数据更全）
    IS_SERVER_ENV: bool = False

    # 邮件服务配置 (用于发送每日报告、价格预警等)
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: Optional[str] = None
    EMAIL_ENABLED: bool = False

    # 浏览器推送配置 (Web Push)
    WEB_PUSH_ENABLED: bool = False
    VAPID_PUBLIC_KEY: Optional[str] = None
    VAPID_PRIVATE_KEY: Optional[str] = None
    WEB_PUSH_CONTACT_EMAIL: Optional[str] = None

settings = Settings()
