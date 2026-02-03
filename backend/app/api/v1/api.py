from fastapi import APIRouter
from app.api.v1.endpoints import auth, portfolio, analysis, user

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
