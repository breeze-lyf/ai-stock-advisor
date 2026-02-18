from sqlalchemy import Column, String, Float, DateTime, Enum, ForeignKey, Boolean, UniqueConstraint, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum
import uuid # Added for uuid.uuid4()

# 市场状态枚举值 (用于判断当前是否可以获取实时交易数据)
class MarketStatus(str, enum.Enum):
    PRE_MARKET = "PRE_MARKET"   # 盘前交易
    OPEN = "OPEN"               # 正常交易时间
    AFTER_HOURS = "AFTER_HOURS" # 盘后交易
    CLOSED = "CLOSED"           # 休市 (周末或节假日)

# 情绪评分枚举
class SentimentScore(str, enum.Enum):
    BULLISH = "BULLISH" # 看多
    BEARISH = "BEARISH" # 看空
    NEUTRAL = "NEUTRAL" # 中性

# 股票基础信息表：存储股票的“户口本”信息（如行业、市值等静态数据）
class Stock(Base):
    __tablename__ = "stocks"

    ticker = Column(String, primary_key=True, index=True) # 股票代码，唯一标识，如 AAPL
    name = Column(String)                                # 股票全称
    sector = Column(String, nullable=True)               # 所属板块 (如：科技)
    industry = Column(String, nullable=True)             # 细分行业 (如：半导体)
    market_cap = Column(Float, nullable=True)            # 总市值
    pe_ratio = Column(Float, nullable=True)              # 滚动市盈率 (Trailing PE)
    forward_pe = Column(Float, nullable=True)            # 预测市盈率 (Forward PE)
    eps = Column(Float, nullable=True)                   # 每股收益
    dividend_yield = Column(Float, nullable=True)        # 股息率
    beta = Column(Float, nullable=True)                  # 贝塔系数 (衡量波动风险)
    fifty_two_week_high = Column(Float, nullable=True)   # 52周内最高成交价
    fifty_two_week_low = Column(Float, nullable=True)    # 52周内最低成交价
    exchange = Column(String, nullable=True)             # 交易所 (如：NASDAQ)
    currency = Column(String, default="USD")             # 计价货币

    # 建立与“实时行情缓存”的一对一关联
    # uselist=False 确保一对一关系，而不是一对多
    market_data = relationship("MarketDataCache", back_populates="stock", uselist=False)
    # 建立与“新闻”的一对多关联
    news = relationship("StockNews", back_populates="stock", cascade="all, delete-orphan")
    # 建立与“投资组合”的一对多关联
    portfolios = relationship("Portfolio", back_populates="stock", cascade="all, delete-orphan")
    # 建立与“AI诊断报告”的一对多关联
    analysis_reports = relationship("AnalysisReport", back_populates="stock", cascade="all, delete-orphan")


# 市场数据缓存表：存储变化极快的价格和技术指标
# 独立成表是为了在频繁更新价格时，不影响基础信息表的稳定性
class MarketDataCache(Base):
    __tablename__ = "market_data_cache"

    ticker = Column(String, ForeignKey("stocks.ticker"), primary_key=True) # 关联的股票代码
    current_price = Column(Float)      # 此时此刻的最新价格
    change_percent = Column(Float)     # 相比昨日收盘的涨跌幅百分比
    
    # --- 为 AI 分析提供的技术指标 (这些值会被喂给 AI 模型) ---
    rsi_14 = Column(Float, nullable=True)     # RSI 相对强弱指标 (0-100)
    ma_20 = Column(Float, nullable=True)       # 20日简单移动平均线
    ma_50 = Column(Float, nullable=True)       # 50日中长期均线
    ma_200 = Column(Float, nullable=True)      # 200日牛熊分界线
    macd_val = Column(Float, nullable=True)    # MACD 指标值
    macd_signal = Column(Float, nullable=True) # MACD 信号线
    macd_hist = Column(Float, nullable=True)   # MACD 柱状图高度
    macd_hist_slope = Column(Float, nullable=True) # 柱线斜率 (判断动能增强还是减弱)
    macd_cross = Column(String, nullable=True)     # MACD 交叉状态 (GOLDEN-金叉 / DEATH-死叉)
    macd_is_new_cross = Column(Boolean, default=False) # 是否是刚产生的交叉 (触发 UI 动画)
    
    # 布林带指标 (用于判断超买超卖)
    bb_upper = Column(Float, nullable=True)    # 布林带上轨 (阻力)
    bb_middle = Column(Float, nullable=True)   # 中轨 (基准)
    bb_lower = Column(Float, nullable=True)    # 下轨 (支撑)
    
    # 波动率与强弱
    atr_14 = Column(Float, nullable=True)      # 平均真实波幅 (衡量波动剧烈程度)
    k_line = Column(Float, nullable=True)      # KDJ 指标 K线
    d_line = Column(Float, nullable=True)      # KDJ 指标 D线
    j_line = Column(Float, nullable=True)      # KDJ 指标 J线 (灵敏线)
    
    # 成交量相关
    volume_ma_20 = Column(Float, nullable=True) # 20日成交量均线
    volume_ratio = Column(Float, nullable=True) # 量比 (成交量活跃度)
    
    # 趋势强度与关键位置
    adx_14 = Column(Float, nullable=True)         # ADX 趋势强度指标
    pivot_point = Column(Float, nullable=True)    # 今日枢轴点 (中轴线)
    resistance_1 = Column(Float, nullable=True)   # 第一阻力位
    resistance_2 = Column(Float, nullable=True)   # 第二阻力位
    support_1 = Column(Float, nullable=True)      # 第一支撑位
    support_2 = Column(Float, nullable=True)      # 第二支撑位
    risk_reward_ratio = Column(Float, nullable=True) # 盈亏比 (Reward/Risk)，本项目核心逻辑
    is_ai_strategy = Column(Boolean, default=False)  # TRUE 代表这是由 AI 锁定的点位，防止被机器算法覆盖
    
    market_status = Column(String, default=MarketStatus.CLOSED.value) # 市场当前状态
    last_updated = Column(DateTime, default=datetime.utcnow, index=True) # 数据最后同步时间

    stock = relationship("Stock", back_populates="market_data")

# 股票新闻表
class StockNews(Base):
    __tablename__ = "stock_news"

    id = Column(String, primary_key=True) # 新闻在全球的唯一 ID
    ticker = Column(String, ForeignKey("stocks.ticker"), index=True) # 属于哪支股票
    title = Column(String, nullable=False)    # 标题
    publisher = Column(String, nullable=True) # 发布媒体
    link = Column(String, nullable=False)     # 原文网页链接
    publish_time = Column(DateTime, nullable=False) # 发布时间
    summary = Column(String, nullable=True)   # AI 总结的新闻摘要
    sentiment = Column(String, nullable=True) # 情绪倾向 (正面/负面/中性)
    
    stock = relationship("Stock", back_populates="news")
