from fastapi import APIRouter
from app.api.v1.endpoints import auth, portfolio, analysis, user, stock, notifications, macro, paper_trading

# 创建 v1 版本的总路由对象
api_router = APIRouter()

# 挂载各业务模块的子路由
# tags 参数用于在 Swagger UI (http://localhost:8000/docs) 中对比 API 进行分类展示

# 认证模块：处理登录、注册、Token 刷新等
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# 投资组合模块：处理自选股的增删改查及实时刷新
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])

# 股票市场模块：处理个股历史行情及详情
api_router.include_router(stock.router, prefix="/stocks", tags=["stocks"])

# AI 分析模块：处理股票的技术面、基本面 AI 分析请求
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])

# 宏观热点模块：处理全球宏观雷达与热点分析
api_router.include_router(macro.router, prefix="/macro", tags=["macro"])

# 用户与设置模块：处理用户信息及 API Key 等偏好设置
api_router.include_router(user.router, prefix="/user", tags=["user"])

# 通知历史模块：展示飞书推送流
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])

# 模拟交易回测模块：处理从今起航的纸面交易
api_router.include_router(paper_trading.router, prefix="/paper-trading", tags=["paper-trading"])
