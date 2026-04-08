"""
策略回测模型
用于存储回测配置和结果
"""
from typing import Optional, Dict, Any
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Text, Numeric, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
from datetime import datetime
from app.core.database import Base


class BacktestConfig(Base):
    """
    回测配置
    用户定义的回测参数和策略规则
    """
    __tablename__ = "backtest_configs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 策略类型
    strategy_type: Mapped[str] = mapped_column(String(50), nullable=False)  # MA_CROSS/RSI_MEAN_REVERSION/MACD/etc.

    # 回测参数
    tickers: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 逗号分隔的股票代码
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 行业
    market: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # US/HK/CN

    # 入场条件（JSON 存储）
    # 示例：{"ma_cross": {"fast": 5, "slow": 20}, "rsi_below": 30}
    entry_conditions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # 出场条件（JSON 存储）
    # 示例：{"stop_loss": 0.1, "take_profit": 0.2, "rsi_above": 70}
    exit_conditions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # 仓位规则
    position_size_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=20.0)  # 每次买入仓位百分比
    max_positions: Mapped[int] = mapped_column(Integer, default=5)  # 最大持仓数

    # 回测区间
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # 资金参数
    initial_capital: Mapped[float] = mapped_column(Numeric(12, 2), default=1000000)  # 初始资金
    commission_rate: Mapped[float] = mapped_column(Numeric(8, 6), default=0.0003)  # 手续费率（万分之三）
    slippage_pct: Mapped[float] = mapped_column(Numeric(5, 4), default=0.001)  # 滑点（0.1%）

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否公开分享

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)


class BacktestResult(Base):
    """
    回测结果
    存储回测执行的详细结果和性能指标
    """
    __tablename__ = "backtest_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    config_id: Mapped[str] = mapped_column(
        ForeignKey("backtest_configs.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    # 回测状态
    status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING/RUNNING/COMPLETED/FAILED
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 执行信息
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    execution_time_seconds: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)

    # 核心绩效指标
    total_return: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)  # 总收益率
    annualized_return: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)  # 年化收益率
    benchmark_return: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)  # 基准收益（如 SPY）

    # 风险指标
    max_drawdown: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)  # 最大回撤
    max_drawdown_duration_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 最大回撤持续天数
    volatility: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)  # 年化波动率
    downside_deviation: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)  # 下行偏差

    # 风险调整收益
    sharpe_ratio: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)  # 夏普比率
    sortino_ratio: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)  # 索提诺比率
    calmar_ratio: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)  # 卡玛比率

    # 交易统计
    total_trades: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    winning_trades: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    losing_trades: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    win_rate: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)  # 胜率
    avg_win_pct: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)  # 平均盈利
    avg_loss_pct: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)  # 平均亏损
    profit_factor: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)  # 盈利因子
    avg_holding_period_days: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)  # 平均持仓天数

    # 最终资金
    final_capital: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    total_commission: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)  # 总手续费

    # 详细数据（JSON 存储）
    # 权益曲线、每日持仓、交易记录等
    equity_curve: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # 权益曲线数据
    trades: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # 交易记录
    monthly_returns: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # 月度收益

    # 元数据
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关系
    config = relationship("BacktestConfig", back_populates="results")


# 添加关系
BacktestConfig.results = relationship("BacktestResult", back_populates="config", cascade="all, delete-orphan")


class SavedStrategy(Base):
    """
    预设策略库
    存储常用的策略模板供用户快速选择
    """
    __tablename__ = "saved_strategies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # TREND/MOMENTUM/MEAN_REVERSION/ARBITRAGE

    # 策略参数模板
    entry_conditions: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    exit_conditions: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    default_position_size: Mapped[float] = mapped_column(Numeric(5, 2), default=20.0)

    # 适用市场
    applicable_markets: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # US,HK,CN
    applicable_sectors: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 逗号分隔

    # 历史表现（供参考）
    historical_return_1y: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)
    historical_sharpe: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)
    historical_max_drawdown: Mapped[Optional[float]] = mapped_column(Numeric(8, 4), nullable=True)

    # 元数据
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)
