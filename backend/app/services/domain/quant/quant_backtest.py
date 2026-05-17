"""
量化回测引擎
事件驱动的回测框架，支持因子组合和多策略回测
"""
import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from app.models.quant_factor import QuantFactor, QuantFactorValue, QuantStrategy, QuantSignal
from app.models.stock import MarketDataCache

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """信号类型"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Position:
    """持仓记录"""
    ticker: str
    quantity: int
    entry_price: float
    entry_date: date
    current_price: float = 0.0
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.entry_price) * self.quantity

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.entry_price == 0:
            return 0.0
        return (self.current_price - self.entry_price) / self.entry_price * 100


@dataclass
class Trade:
    """交易记录"""
    ticker: str
    trade_type: SignalType
    quantity: int
    price: float
    trade_date: date
    commission: float = 0.0
    slippage: float = 0.0
    signal_id: Optional[str] = None

    @property
    def total_cost(self) -> float:
        if self.trade_type == SignalType.BUY:
            return self.quantity * self.price + self.commission + self.slippage
        else:
            return self.quantity * self.price - self.commission - self.slippage


@dataclass
class BacktestConfig:
    """回测配置"""
    name: str
    start_date: date
    end_date: date
    initial_capital: float = 1000000.0
    commission_rate: float = 0.0003  # 万分之三
    slippage_rate: float = 0.001  # 千分之一
    max_position_pct: float = 10.0  # 单个股最大仓位%
    max_stocks: int = 50  # 最大持仓数
    stop_loss_pct: float = 10.0  # 止损线%
    take_profit_pct: float = 30.0  # 止盈线%
    rebalance_frequency: str = "WEEKLY"  # DAILY/WEEKLY/MONTHLY


@dataclass
class BacktestResult:
    """回测结果"""
    config: BacktestConfig
    total_return: float = 0.0
    annual_return: float = 0.0
    benchmark_return: Optional[float] = None
    excess_return: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    max_drawdown_duration_days: Optional[int] = None
    volatility: Optional[float] = None
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: Optional[float] = None
    avg_win_pct: Optional[float] = None
    avg_loss_pct: Optional[float] = None
    profit_factor: Optional[float] = None
    avg_holding_days: Optional[float] = None
    turnover_rate: Optional[float] = None
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    positions_history: List[Dict[str, Any]] = field(default_factory=list)
    trades: List[Trade] = field(default_factory=list)
    monthly_returns: Dict[str, float] = field(default_factory=dict)


class QuantitativeBacktestEngine:
    """
    量化回测引擎

    功能：
    1. 事件驱动回测框架
    2. 因子信号生成
    3. 组合再平衡
    4. 交易成本管理
    5. 绩效归因分析
    """

    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.cash: float = 0.0
        self.portfolio_value: float = 0.0
        self.equity_curve: List[Dict[str, Any]] = []
        self.trades: List[Trade] = []
        self.daily_returns: List[float] = []

    async def run_backtest(
        self,
        db: AsyncSession,
        config: BacktestConfig,
        strategy_id: Optional[str] = None,
        factor_ids: Optional[List[str]] = None,
    ) -> BacktestResult:
        """
        执行回测

        Args:
            db: 数据库会话
            config: 回测配置
            strategy_id: 策略 ID（可选）
            factor_ids: 因子 ID 列表（可选）

        Returns:
            BacktestResult: 回测结果
        """
        # 初始化
        self.cash = config.initial_capital
        self.portfolio_value = config.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []

        # 获取回测期内的交易日
        trade_dates = await self._get_trade_dates(db, config.start_date, config.end_date)
        if not trade_dates:
            logger.error("No trade dates found")
            return BacktestResult(config=config)

        # 获取股票池
        stock_pool = await self._get_stock_pool(db, config.start_date)

        prev_value = self.portfolio_value
        prev_date = config.start_date

        # 主回测循环
        for current_date in trade_dates:
            # 更新持仓价格
            await self._update_positions(db, current_date, stock_pool)

            # 计算当前组合价值
            self.portfolio_value = self.cash + sum(p.market_value for p in self.positions.values())

            # 记录权益曲线
            self.equity_curve.append({
                'date': current_date.isoformat(),
                'equity': round(self.portfolio_value, 2),
                'cash': round(self.cash, 2),
                'position_value': round(self.portfolio_value - self.cash, 2),
            })

            # 计算日收益
            if prev_value > 0:
                daily_ret = (self.portfolio_value - prev_value) / prev_value
                self.daily_returns.append(daily_ret)

            # 检查是否需要再平衡
            should_rebalance = self._should_rebalance(current_date, prev_date, config.rebalance_frequency)

            if should_rebalance:
                # 生成交易信号
                signals = await self._generate_signals(
                    db, current_date, factor_ids, stock_pool
                )

                # 【事件驱动核心：信号执行】
                # 基于当前生成的量化信号（买入/卖出），在当前的现金流限制和仓位限制下模拟撮合交易。
                await self._execute_trades(db, signals, current_date, config)

                prev_date = current_date
                prev_value = self.portfolio_value

            # 【事件驱动核心：止损止盈检查】
            # 在每日收盘前，根据各持仓的当前价格，检查是否触及预设的止损/止盈阈值。
            # 这有助于模拟真实交易中的风险控制逻辑。
            await self._check_stop_loss_take_profit(db, current_date, config)

        # 计算回测结果
        result = self._calculate_performance_metrics(config)
        result.trades = self.trades
        result.equity_curve = self.equity_curve

        return result

    async def _get_trade_dates(
        self,
        db: AsyncSession,
        start_date: date,
        end_date: date,
    ) -> List[date]:
        """获取交易日期列表"""
        stmt = select(MarketDataCache.trade_date).where(
            and_(
                MarketDataCache.trade_date >= start_date,
                MarketDataCache.trade_date <= end_date,
            )
        ).distinct().order_by(MarketDataCache.trade_date)

        result = await db.execute(stmt)
        dates = result.scalars().all()
        return [d.date() if isinstance(d, datetime) else d for d in dates]

    async def _get_stock_pool(
        self,
        db: AsyncSession,
        start_date: date,
    ) -> List[str]:
        """获取股票池"""
        # 获取有市场数据的股票
        stmt = select(MarketDataCache.ticker).where(
            MarketDataCache.trade_date >= start_date
        ).distinct()
        result = await db.execute(stmt)
        return result.scalars().all()

    async def _update_positions(
        self,
        db: AsyncSession,
        current_date: date,
        stock_pool: List[str],
    ):
        """更新持仓价格"""
        for ticker, position in self.positions.items():
            stmt = select(MarketDataCache.close_price).where(
                and_(
                    MarketDataCache.ticker == ticker,
                    MarketDataCache.trade_date == current_date,
                )
            )
            result = await db.execute(stmt)
            price = result.scalar()
            if price:
                position.current_price = float(price)

    def _should_rebalance(
        self,
        current_date: date,
        prev_date: date,
        frequency: str,
    ) -> bool:
        """判断是否需要再平衡"""
        if frequency == "DAILY":
            return True
        elif frequency == "WEEKLY":
            # 每周一再平衡
            return current_date.weekday() == 0
        elif frequency == "MONTHLY":
            # 每月第一个交易日再平衡
            return current_date.day <= 5
        elif frequency == "QUARTERLY":
            # 每季度第一个月再平衡
            return current_date.month in [1, 4, 7, 10] and current_date.day <= 5
        return False

    async def _generate_signals(
        self,
        db: AsyncSession,
        current_date: date,
        factor_ids: Optional[List[str]],
        stock_pool: List[str],
    ) -> Dict[str, SignalType]:
        """
        生成交易信号

        基于因子值排序生成信号
        """
        if not factor_ids:
            return {}

        signals = {}

        # 获取所有因子值
        for factor_id in factor_ids:
            stmt = select(QuantFactorValue).where(
                and_(
                    QuantFactorValue.factor_id == factor_id,
                    QuantFactorValue.trade_date == current_date,
                )
            )
            result = await db.execute(stmt)
            factor_values = result.scalars().all()

            if factor_values:
                # 转换为 DataFrame 并排序
                df = pd.DataFrame([{
                    'ticker': fv.ticker,
                    'value': fv.zscore_value or fv.rank_value or fv.value,
                } for fv in factor_values])

                # 按因子值排序，选 top 作为买入信号
                df = df.dropna(subset=['value'])
                df = df.sort_values('value', ascending=False)

                # 选前 N 只股票作为买入候选
                top_n = min(20, len(df))
                for ticker in df.head(top_n)['ticker']:
                    if ticker not in self.positions:
                        signals[ticker] = SignalType.BUY

        return signals

    async def _execute_trades(
        self,
        db: AsyncSession,
        signals: Dict[str, SignalType],
        current_date: date,
        config: BacktestConfig,
    ):
        """执行交易"""
        # 获取当前价格
        for ticker, signal_type in signals.items():
            stmt = select(MarketDataCache.close_price).where(
                and_(
                    MarketDataCache.ticker == ticker,
                    MarketDataCache.trade_date == current_date,
                )
            )
            result = await db.execute(stmt)
            price = result.scalar()

            if not price:
                continue

            price = float(price)

            if signal_type == SignalType.BUY:
                # 检查是否已有持仓
                if ticker in self.positions:
                    continue

                # 检查最大持仓数
                if len(self.positions) >= config.max_stocks:
                    continue

                # 计算买入数量
                max_position_value = self.portfolio_value * config.max_position_pct / 100
                quantity = int(max_position_value / price / 100) * 100  # 100 股整数倍

                if quantity < 100:
                    continue

                # 计算交易成本
                trade_value = quantity * price
                commission = trade_value * config.commission_rate
                slippage = trade_value * config.slippage_rate

                if trade_value + commission + slippage > self.cash:
                    continue

                # 创建持仓
                self.positions[ticker] = Position(
                    ticker=ticker,
                    quantity=quantity,
                    entry_price=price,
                    entry_date=current_date,
                    current_price=price,
                    stop_loss_price=price * (1 - config.stop_loss_pct / 100),
                    take_profit_price=price * (1 + config.take_profit_pct / 100),
                )

                # 更新现金
                self.cash -= (trade_value + commission + slippage)

                # 记录交易
                self.trades.append(Trade(
                    ticker=ticker,
                    trade_type=SignalType.BUY,
                    quantity=quantity,
                    price=price,
                    trade_date=current_date,
                    commission=commission,
                    slippage=slippage,
                ))

            elif signal_type == SignalType.SELL:
                if ticker not in self.positions:
                    continue

                position = self.positions[ticker]
                trade_value = position.quantity * price
                commission = trade_value * config.commission_rate
                slippage = trade_value * config.slippage_rate

                # 更新现金
                self.cash += (trade_value - commission - slippage)

                # 记录交易
                self.trades.append(Trade(
                    ticker=ticker,
                    trade_type=SignalType.SELL,
                    quantity=position.quantity,
                    price=price,
                    trade_date=current_date,
                    commission=commission,
                    slippage=slippage,
                ))

                # 删除持仓
                del self.positions[ticker]

    async def _check_stop_loss_take_profit(
        self,
        db: AsyncSession,
        current_date: date,
        config: BacktestConfig,
    ):
        """检查止损止盈"""
        to_sell = []

        for ticker, position in self.positions.items():
            # 获取当前价格
            stmt = select(MarketDataCache.close_price).where(
                and_(
                    MarketDataCache.ticker == ticker,
                    MarketDataCache.trade_date == current_date,
                )
            )
            result = await db.execute(stmt)
            price = result.scalar()

            if not price:
                continue

            price = float(price)
            position.current_price = price

            # 检查止损
            if position.stop_loss_price and price <= position.stop_loss_price:
                to_sell.append(ticker)
                continue

            # 检查止盈
            if position.take_profit_price and price >= position.take_profit_price:
                to_sell.append(ticker)

        # 执行卖出
        for ticker in to_sell:
            position = self.positions[ticker]
            trade_value = position.quantity * position.current_price
            commission = trade_value * config.commission_rate
            slippage = trade_value * config.slippage_rate

            self.cash += (trade_value - commission - slippage)

            self.trades.append(Trade(
                ticker=ticker,
                trade_type=SignalType.SELL,
                quantity=position.quantity,
                price=position.current_price,
                trade_date=current_date,
                commission=commission,
                slippage=slippage,
            ))

            del self.positions[ticker]

    def _calculate_performance_metrics(
        self,
        config: BacktestConfig,
    ) -> BacktestResult:
        """计算绩效指标"""
        result = BacktestResult(config=config)

        if not self.equity_curve:
            return result

        # 权益曲线 DataFrame
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df['date'] = pd.to_datetime(equity_df['date'])

        # 总收益率
        initial_equity = equity_df['equity'].iloc[0]
        final_equity = equity_df['equity'].iloc[-1]
        result.total_return = (final_equity - initial_equity) / initial_equity * 100

        # 年化收益率
        days = (equity_df['date'].iloc[-1] - equity_df['date'].iloc[0]).days
        if days > 0:
            result.annual_return = ((final_equity / initial_equity) ** (365 / days) - 1) * 100

        # 波动率
        if self.daily_returns:
            result.volatility = np.std(self.daily_returns) * np.sqrt(252) * 100

            # 夏普比率 (Sharpe Ratio)
            # 逻辑：衡量每承受一单位总风险（标准差）所获得的超额收益。
            # 公式：(年化收益率 - 无风险利率) / 年化波动率
            if result.volatility and result.volatility > 0:
                excess_return = result.annual_return - self.risk_free_rate * 100
                result.sharpe_ratio = excess_return / result.volatility

            # 索提诺比率 (Sortino Ratio)
            # 逻辑：夏普比率的改进版。它只关注“下行波动率”（即亏损时的风险），
            # 认为向上的波动对投资者是有利的，不应计入惩罚项。
            negative_returns = [r for r in self.daily_returns if r < 0]
            if negative_returns:
                downside_vol = np.std(negative_returns) * np.sqrt(252) * 100
                if downside_vol > 0:
                    result.sortino_ratio = excess_return / downside_vol

        # 最大回撤
        equity_df['cummax'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['cummax']) / equity_df['cummax'] * 100
        result.max_drawdown = equity_df['drawdown'].min()

        # 最大回撤持续期
        drawdown_periods = self._calculate_drawdown_duration(equity_df)
        result.max_drawdown_duration_days = drawdown_periods

        # 交易统计
        result.total_trades = len(self.trades)

        # 计算盈亏交易
        buy_trades = {}
        for trade in self.trades:
            if trade.trade_type == SignalType.BUY:
                buy_trades[trade.ticker] = trade
            elif trade.trade_type == SignalType.SELL and trade.ticker in buy_trades:
                buy_trade = buy_trades[trade.ticker]
                pnl = (trade.price - buy_trade.price) * trade.quantity - buy_trade.commission - trade.commission
                if pnl > 0:
                    result.winning_trades += 1
                else:
                    result.losing_trades += 1

        total_closed = result.winning_trades + result.losing_trades
        if total_closed > 0:
            result.win_rate = result.winning_trades / total_closed * 100

        # 平均持仓天数
        if self.trades:
            holding_days = []
            buy_dates = {}
            for trade in self.trades:
                if trade.trade_type == SignalType.BUY:
                    buy_dates[trade.ticker] = trade.trade_date
                elif trade.trade_type == SignalType.SELL and trade.ticker in buy_dates:
                    days = (trade.trade_date - buy_dates[trade.ticker]).days
                    holding_days.append(days)

            if holding_days:
                result.avg_holding_days = np.mean(holding_days)

        # 月度收益
        equity_df['month'] = equity_df['date'].dt.to_period('M')
        monthly = equity_df.groupby('month')['equity'].apply(lambda x: (x.iloc[-1] - x.iloc[0]) / x.iloc[0] * 100)
        result.monthly_returns = {str(k): round(v, 4) for k, v in monthly.to_dict().items()}

        # 换手率
        total_turnover = sum(t.quantity * t.price for t in self.trades)
        avg_portfolio_value = (initial_equity + final_equity) / 2
        if avg_portfolio_value > 0 and days > 0:
            result.turnover_rate = (total_turnover / avg_portfolio_value) * (252 / days) * 100

        return result

    def _calculate_drawdown_duration(
        self,
        equity_df: pd.DataFrame,
    ) -> int:
        """计算最大回撤持续期（天数）"""
        equity_df = equity_df.copy()
        equity_df['in_drawdown'] = equity_df['drawdown'] < 0

        max_duration = 0
        current_duration = 0

        for in_dd in equity_df['in_drawdown']:
            if in_dd:
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0

        return max_duration


# 全局单例
quant_backtest_engine = QuantitativeBacktestEngine()
