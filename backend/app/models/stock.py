from sqlalchemy import Column, String, Float, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum

# 市场状态枚举值
class MarketStatus(str, enum.Enum):
    PRE_MARKET = "PRE_MARKET"   # 盘前
    OPEN = "OPEN"               # 交易中
    AFTER_HOURS = "AFTER_HOURS" # 盘后
    CLOSED = "CLOSED"           # 休市

# 股票基础信息表：存储股票的静态数据（如行业、市值等）
class Stock(Base):
    __tablename__ = "stocks"

    ticker = Column(String, primary_key=True, index=True) # 股票代码，如 AAPL, 600519.SH
    name = Column(String)                                # 股票名称
    sector = Column(String, nullable=True)               # 板块/部门
    industry = Column(String, nullable=True)             # 细分行业
    market_cap = Column(Float, nullable=True)            # 市值
    pe_ratio = Column(Float, nullable=True)              # 市盈率 (Trailing PE)
    forward_pe = Column(Float, nullable=True)            # 预测市盈率 (Forward PE)
    eps = Column(Float, nullable=True)                   # 每股收益 (EPS)
    dividend_yield = Column(Float, nullable=True)        # 股息率
    beta = Column(Float, nullable=True)                  # 贝塔系数（风险指标）
    fifty_two_week_high = Column(Float, nullable=True)   # 52周最高
    fifty_two_week_low = Column(Float, nullable=True)    # 52周最低
    exchange = Column(String, nullable=True)             # 交易所
    currency = Column(String, default="USD")             # 货币单位

    # 与实时行情缓存的一对一关系
    market_data = relationship("MarketDataCache", back_populates="stock", uselist=False)

# 市场数据缓存表：存储需要频繁更新的实时报价和技术指标
class MarketDataCache(Base):
    __tablename__ = "market_data_cache"

    ticker = Column(String, ForeignKey("stocks.ticker"), primary_key=True)
    current_price = Column(Float)      # 当前最新价
    change_percent = Column(Float)     # 涨跌幅百分比
    
    # 为 AI 分析预留的技术指标
    rsi_14 = Column(Float, nullable=True)     # RSI 强弱指标
    ma_20 = Column(Float, nullable=True)       # 20日均线
    ma_50 = Column(Float, nullable=True)       # 50日均线
    ma_200 = Column(Float, nullable=True)      # 200日均线
    macd_val = Column(Float, nullable=True)    # MACD 值
    macd_signal = Column(Float, nullable=True) # 信号线
    macd_hist = Column(Float, nullable=True)   # 柱状图
    macd_hist_slope = Column(Float, nullable=True) # 柱线斜率 (一阶导数)
    
    # 布林带指标
    bb_upper = Column(Float, nullable=True)    # 上轨
    bb_middle = Column(Float, nullable=True)   # 中轨
    bb_lower = Column(Float, nullable=True)    # 下轨
    
    # ATR 与 KDJ
    atr_14 = Column(Float, nullable=True)      # 平均真实波幅
    k_line = Column(Float, nullable=True)      # KDJ-K
    d_line = Column(Float, nullable=True)      # KDJ-D
    j_line = Column(Float, nullable=True)      # KDJ-J
    
    # 成交量相关
    volume_ma_20 = Column(Float, nullable=True) # 20日成交量均线
    # 量比
    volume_ratio = Column(Float, nullable=True) 
    
    # ADX & 支撑阻力位
    adx_14 = Column(Float, nullable=True)         # ADX 趋势强度
    pivot_point = Column(Float, nullable=True)    # 枢轴点
    resistance_1 = Column(Float, nullable=True)   # 阻力位 R1
    resistance_2 = Column(Float, nullable=True)   # 阻力位 R2
    support_1 = Column(Float, nullable=True)      # 支撑位 S1
    support_2 = Column(Float, nullable=True)      # 支撑位 S2
    
    market_status = Column(String, default=MarketStatus.CLOSED.value) # 市场状态
    last_updated = Column(DateTime, default=datetime.utcnow, index=True) # 最后更新时间

    stock = relationship("Stock", back_populates="market_data")

# 股票相关新闻表
class StockNews(Base):
    __tablename__ = "stock_news"

    id = Column(String, primary_key=True) # 新闻唯一标识（通常由数据源提供）
    ticker = Column(String, ForeignKey("stocks.ticker"), index=True)
    title = Column(String, nullable=False)    # 标题
    publisher = Column(String, nullable=True) # 发布者
    link = Column(String, nullable=False)     # 链接
    publish_time = Column(DateTime, nullable=False) # 发布时间
    summary = Column(String, nullable=True)   # AI 生成的摘要或原始摘要
    sentiment = Column(String, nullable=True) # 情感分析结果 (预留)
    
    stock = relationship("Stock", back_populates="news")

# 定义反向关联逻辑
Stock.news = relationship("StockNews", back_populates="stock", cascade="all, delete-orphan")
Stock.market_data = relationship("MarketDataCache", back_populates="stock", uselist=False)
