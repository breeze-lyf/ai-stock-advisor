from fastapi import APIRouter
from app.api.v1.endpoints import auth, portfolio, analysis, user

# 创建 v1 版本的总路由对象
# 在 RESTful 架构中，版本化（v1/v2）是保证 API 向后兼容性的重要手段
api_router = APIRouter()

# 挂载各业务模块的子路由
# tags 参数用于在 Swagger UI (http://localhost:8000/docs) 中对比 API 进行分类展示

# 认证模块：处理登录、注册、Token 刷新等
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# 投资组合模块：处理自选股的增删改查及实时刷新
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])

# AI 分析模块：处理股票的技术面、基本面 AI 分析请求
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])

# 用户与设置模块：处理用户信息及 API Key 等偏好设置
api_router.include_router(user.router, prefix="/user", tags=["user"])
