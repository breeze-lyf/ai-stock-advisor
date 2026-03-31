from datetime import datetime, timedelta
import logging
import math
from typing import Any, Union
from jose import jwt
import bcrypt
from cryptography.fernet import Fernet
from app.core.config import settings
from app.utils.time import utc_now_naive

ALGORITHM = "HS256"
logger = logging.getLogger(__name__)

def encrypt_api_key(api_key: str) -> str:
    if not api_key:
        return None
    if not settings.ENCRYPTION_KEY:
        raise ValueError(
            "ENCRYPTION_KEY is not configured. Cannot store API keys securely. "
            "Generate a key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    if not encrypted_key:
        return None
    if not settings.ENCRYPTION_KEY:
        logger.warning("ENCRYPTION_KEY not set — returning stored value as-is (may be plaintext legacy data)")
        return encrypted_key
    try:
        f = Fernet(settings.ENCRYPTION_KEY.encode())
        return f.decrypt(encrypted_key.encode()).decode()
    except Exception:
        # Backward compat: data stored before encryption was enabled
        return encrypted_key

def sanitize_float(val: Any, default: Any = None) -> Any:
    """
    数值清洗工具 (Numeric Sanitizer)
    职责：防止 NaN (非数字) 或 Inf (无穷大) 导致 JSON 序列化崩溃。
    常用于从金融数据源 (如 AkShare, IBKR) 或 TA 库抓取的数据。
    """
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = utc_now_naive() + expires_delta
    else:
        expire = utc_now_naive() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any]) -> str:
    expire = utc_now_naive() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode and verify any JWT (access or refresh). Raises JWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # bcrypt 4.x 有 72 字节限制，截断密码
    truncated = plain_password.encode('utf-8')[:72]
    return bcrypt.checkpw(truncated, hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    # bcrypt 4.x 有 72 字节限制，截断密码
    truncated = password.encode('utf-8')[:72]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode('utf-8')
