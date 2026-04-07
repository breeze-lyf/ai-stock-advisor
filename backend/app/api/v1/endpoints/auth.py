from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from jose import JWTError

from app.core import security
from app.core.database import get_db
from app.core.rate_limiter import limiter
from app.infrastructure.db.repositories.user_repository import UserRepository
from app.models.user import User

router = APIRouter()


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshRequest(BaseModel):
    refresh_token: str


def _issue_tokens(user_id) -> dict:
    """Create a matched access + refresh token pair for a user."""
    return {
        "access_token": security.create_access_token(user_id),
        "refresh_token": security.create_refresh_token(user_id),
        "token_type": "bearer",
    }


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login_access_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    用户登录接口 — 返回 Access Token + Refresh Token。
    限流：每 IP 每分钟最多 10 次登录尝试。
    """
    user = await UserRepository(db).get_by_email(form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    return _issue_tokens(user.id)


@router.post("/register", response_model=Token)
async def register_user(
    user_in: UserCreate, db: AsyncSession = Depends(get_db)
) -> Any:
    """
    用户注册接口 — 注册成功后直接返回 Token 实现自动登录。
    """
    repo = UserRepository(db)
    existing_user = await repo.get_by_email(user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
    )
    user = await repo.create(user)
    return _issue_tokens(user.id)


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    用 Refresh Token 换取新的 Access Token + Refresh Token 对（rolling refresh）。
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = security.decode_token(body.refresh_token)
    except JWTError:
        raise credentials_error

    if payload.get("type") != "refresh":
        raise credentials_error

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_error

    user = await UserRepository(db).get_by_id(user_id)
    if not user:
        raise credentials_error

    return _issue_tokens(user.id)

