import fastapi
from app.api.v1.endpoints import auth, portfolio, analysis, user, stock, notifications, macro, paper_trading, user_preferences, enhanced_analysis, stock_lists, screener, portfolio_risk, calendar, notification_settings, signals, user_profile, academy, backtest, subscription, monitoring, quant_factors

# 创建 v1 版本的总路由对象
api_router = fastapi.APIRouter()

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

# 增强 AI 分析模块：提供情景分析、风险分析、多时间框架分析
api_router.include_router(enhanced_analysis.router, prefix="/analysis/enhanced", tags=["enhanced-analysis"])

# 股票列表模块：支持多列表管理
api_router.include_router(stock_lists.router, prefix="/portfolio", tags=["stock-lists"])

# 选股器模块：提供预设策略和自定义筛选
api_router.include_router(screener.router, prefix="/screener", tags=["screener"])

# 投资组合风险分析模块
api_router.include_router(portfolio_risk.router, prefix="/portfolio", tags=["portfolio-risk"])

# 财经日历模块
api_router.include_router(calendar.router, prefix="/calendar", tags=["calendar"])

# 宏观热点模块：处理全球宏观雷达与热点分析
api_router.include_router(macro.router, prefix="/macro", tags=["macro"])

# 用户与设置模块：处理用户信息及 API Key 等偏好设置
api_router.include_router(user.router, prefix="/user", tags=["user"])

# 用户偏好设置模块：处理用户投资偏好、通知偏好等
api_router.include_router(user_preferences.router, prefix="/user-preferences", tags=["user-preferences"])

# 通知历史模块：展示飞书推送流
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])

# 通知设置模块：管理用户通知偏好、订阅和浏览器推送
api_router.include_router(notification_settings.router, prefix="/notification-settings", tags=["notification-settings"])

# AI 信号历史模块：追踪 AI 分析建议的表现
api_router.include_router(signals.router, prefix="/signals", tags=["signals"])

# 用户投资画像模块：管理用户投资偏好和仪表盘配置
api_router.include_router(user_profile.router, prefix="/user-profile", tags=["user-profile"])

# 投资者教育中心模块：提供课程学习和测验
api_router.include_router(academy.router, prefix="/academy", tags=["academy"])

# 策略回测模块：提供策略回测功能
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])

# 会员订阅模块：管理订阅计划和支付
api_router.include_router(subscription.router, prefix="/subscription", tags=["subscription"])

# 系统监控模块：提供健康检查和错误日志查询
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])

# 模拟交易回测模块：处理从今起航的纸面交易
api_router.include_router(paper_trading.router, prefix="/paper-trading", tags=["paper-trading"])

# 量化因子模块：提供因子管理、分析、回测和优化
api_router.include_router(quant_factors.router, prefix="/quant", tags=["quant"])
