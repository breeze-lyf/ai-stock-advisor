from datetime import datetime, timedelta
import math
from typing import Any, Union
from jose import jwt
import bcrypt
from cryptography.fernet import Fernet
from app.core.config import settings

ALGORITHM = "HS256"

def encrypt_api_key(api_key: str) -> str:
    if not api_key:
        return None
    if not settings.ENCRYPTION_KEY:
        return api_key # Fallback if key not set (not recommended for production)
    f = Fernet(settings.ENCRYPTION_KEY.encode())
    return f.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    if not encrypted_key:
        return None
    if not settings.ENCRYPTION_KEY:
        return encrypted_key # Fallback
    try:
        f = Fernet(settings.ENCRYPTION_KEY.encode())
        return f.decrypt(encrypted_key.encode()).decode()
    except Exception:
        return encrypted_key # If decryption fails, return as is (might be old plain data)

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
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # bcrypt 4.x 有 72 字节限制，截断密码
    truncated = plain_password.encode('utf-8')[:72]
    return bcrypt.checkpw(truncated, hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    # bcrypt 4.x 有 72 字节限制，截断密码
    truncated = password.encode('utf-8')[:72]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode('utf-8')
