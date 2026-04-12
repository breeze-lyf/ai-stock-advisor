"""
量化因子模型
定义因子的元数据、计算配置和表现指标
"""
from typing import Optional, Dict, Any
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Text, Numeric, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime
from app.core.database import Base


class QuantFactor(Base):
    """
    量化因子定义

    存储因子的元数据、计算配置和性能指标
    """
    __tablename__ = "quant_factors"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)  # 因子名称
    code_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # 代码名称 (如 MOMENTUM_12M)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # 因子类别

    # 因子描述
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    formula: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 计算公式描述

    # 计算配置
    calculation_params: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    lookback_period: Mapped[int] = mapped_column(Integer, default=252)  # 回溯期 (交易日)
    decay_period: Mapped[int] = mapped_column(Integer, default=0)  # 衰减期

    # 数据源配置
    data_source: Mapped[str] = mapped_column(String(50), default="market_data")  # market_data/financial_data
    frequency: Mapped[str] = mapped_column(String(20), default="DAILY")  # DAILY/WEEKLY/MONTHLY

    # 因子表现指标 (Factor Metrics)
    # IC (Information Coefficient): 因子值与下期收益率的相关系数。IC > 0.05 且稳定则认为因子有效。
    ic_mean: Mapped[Optional[float]] = mapped_column(Numeric(8, 6), nullable=True)
    # IR (Information Ratio): IC 的均值 / IC 的标准差，代表因子的稳定性和风险调整后收益。
    ic_ir: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    rank_ic_mean: Mapped[Optional[float]] = mapped_column(Numeric(8, 6), nullable=True)
    rank_ic_ir: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)

    # 回测表现 (Backtest Results)
    annual_return: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    # 夏普比率：超额收益 / 总风险，衡量每一单位风险带来的超额回报。
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    max_drawdown: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    win_rate: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)
    # 换手率：反映组合调整的频率，过高会增加摩擦成本（佣金/印花税）。
    turnover_rate: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否公开
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否自定义因子

    # 元数据
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)

    # 关系
    values = relationship("QuantFactorValue", back_populates="factor", cascade="all, delete-orphan")
    backtest_results = relationship("QuantBacktestResult", back_populates="factor", cascade="all, delete-orphan")


class QuantFactorValue(Base):
    """
    因子值存储

    存储每日因子值（横截面数据）
    """
    __tablename__ = "quant_factor_values"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    factor_id: Mapped[str] = mapped_column(
        ForeignKey("quant_factors.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    trade_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # 因子值
    value: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    zscore_value: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)  # 标准化值
    rank_value: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)  # 排序值 (0-1)

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    factor = relationship("QuantFactor", back_populates="values")

    __table_args__ = (
        UniqueConstraint('factor_id', 'ticker', 'trade_date', name='uq_factor_ticker_date'),
    )


class QuantStrategy(Base):
    """
    量化策略定义

    存储多因子组合策略的配置
    """
    __tablename__ = "quant_strategies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 策略类型
    strategy_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # FACTOR_LONG_ONLY: 纯多头
    # FACTOR_LONG_SHORT: 多空对冲
    # MARKET_NEUTRAL: 市场中性

    # 因子权重配置
    factor_weights: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # 示例：{"factor_1_id": 0.3, "factor_2_id": 0.5}

    # 调仓频率
    rebalance_frequency: Mapped[str] = mapped_column(String(20), default="WEEKLY")
    # DAILY / WEEKLY / MONTHLY / QUARTERLY

    # 交易参数
    max_position_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=10.0)  # 单个股最大仓位%
    max_sector_exposure: Mapped[float] = mapped_column(Numeric(5, 2), default=30.0)  # 最大行业暴露%
    min_market_cap: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)  # 最小市值
    max_stocks: Mapped[int] = mapped_column(Integer, default=50)  # 最大持仓数

    # 风控参数
    turnover_limit: Mapped[float] = mapped_column(Numeric(5, 2), default=50.0)  # 换手率限制%
    stop_loss_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=10.0)  # 止损线%

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_backtesting: Mapped[bool] = mapped_column(Boolean, default=False)

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)

    # 关系
    signals = relationship("QuantSignal", back_populates="strategy", cascade="all, delete-orphan")
    backtest_results = relationship("QuantBacktestResult", back_populates="strategy", cascade="all, delete-orphan")


class QuantSignal(Base):
    """
    量化交易信号

    存储策略生成的交易信号
    """
    __tablename__ = "quant_signals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_id: Mapped[str] = mapped_column(
        ForeignKey("quant_strategies.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    signal_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # 信号信息
    signal_strength: Mapped[float] = mapped_column(Numeric(6, 4), default=0.0)  # -1 到 1
    target_weight: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)  # 目标权重%
    current_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)

    # 因子得分明细
    factor_scores: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    # PENDING / EXECUTED / CANCELLED / EXPIRED

    # 执行信息
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    executed_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    executed_volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    strategy = relationship("QuantStrategy", back_populates="signals")


class QuantBacktestResult(Base):
    """
    量化回测结果

    存储因子或策略的回测表现
    """
    __tablename__ = "quant_backtest_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 关联
    factor_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("quant_factors.id", ondelete="CASCADE"),
        index=True,
        nullable=True
    )
    strategy_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("quant_strategies.id", ondelete="CASCADE"),
        index=True,
        nullable=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    # 回测配置
    backtest_name: Mapped[str] = mapped_column(String(200), nullable=False)
    backtest_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    backtest_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    initial_capital: Mapped[float] = mapped_column(Numeric(14, 2), default=1000000)
    commission_rate: Mapped[float] = mapped_column(Numeric(8, 6), default=0.0003)
    slippage_rate: Mapped[float] = mapped_column(Numeric(8, 6), default=0.001)

    # 回测参数
    backtest_params: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # 绩效指标
    total_return: Mapped[float] = mapped_column(Numeric(10, 4), default=0.0)
    annual_return: Mapped[float] = mapped_column(Numeric(10, 4), default=0.0)
    benchmark_return: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    excess_return: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)

    # 风险指标
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    sortino_ratio: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    calmar_ratio: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    max_drawdown: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    max_drawdown_duration_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    volatility: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    beta: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    alpha: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)

    # 交易统计
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)
    avg_win_pct: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    avg_loss_pct: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    profit_factor: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    avg_holding_days: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    turnover_rate: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)

    # 因子表现（仅因子回测）
    ic_mean: Mapped[Optional[float]] = mapped_column(Numeric(8, 6), nullable=True)
    ic_ir: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    rank_ic_mean: Mapped[Optional[float]] = mapped_column(Numeric(8, 6), nullable=True)
    rank_ic_ir: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)

    # 最终资金
    final_capital: Mapped[float] = mapped_column(Numeric(14, 2), default=0.0)
    total_commission: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)

    # 详细数据（JSON 存储）
    equity_curve: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    positions_history: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    trades: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    monthly_returns: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="COMPLETED")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 元数据
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # 关系
    factor = relationship("QuantFactor", back_populates="backtest_results")
    strategy = relationship("QuantStrategy", back_populates="backtest_results")


class FactorICHistory(Base):
    """
    因子 IC 历史统计

    存储每日/每周的 IC 值用于分析
    """
    __tablename__ = "factor_ic_history"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    factor_id: Mapped[str] = mapped_column(
        ForeignKey("quant_factors.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    # 统计周期
    stat_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    stat_period: Mapped[str] = mapped_column(String(20), default="DAILY")  # DAILY / WEEKLY / MONTHLY

    # IC 值
    ic: Mapped[Optional[float]] = mapped_column(Numeric(8, 6), nullable=True)
    rank_ic: Mapped[Optional[float]] = mapped_column(Numeric(8, 6), nullable=True)

    # 多头收益（Top 组合）
    long_return: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)

    # 空头收益（Bottom 组合）
    short_return: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)

    # 多空收益
    long_short_return: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    factor = relationship("QuantFactor")


class QuantOptimizationConfig(Base):
    """
    组合优化配置

    存储组合优化的参数配置
    """
    __tablename__ = "quant_optimization_configs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 优化器类型
    optimizer_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # MEAN_VARIANCE: 均值方差
    # BLACK_LITTERMAN: BL 模型
    # RISK_PARITY: 风险平价
    # HRP: 层次风险平价
    # MIN_VOLATILITY: 最小波动率
    # MAX_SHARPE: 最大夏普

    # 优化参数
    risk_aversion: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    target_return: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)
    target_volatility: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)

    # 权重约束
    max_weight: Mapped[float] = mapped_column(Numeric(5, 2), default=10.0)
    min_weight: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)

    # 行业约束
    sector_constraints: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # 示例：{"technology": 30, "healthcare": 20}

    # 其他约束
    max_turnover: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    benchmark_tracking_error: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)

    # 元数据
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)
