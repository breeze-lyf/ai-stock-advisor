"""
策略回测引擎
执行回测并计算绩效指标
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
import numpy as np

from app.models.backtest import BacktestConfig, BacktestResult, SavedStrategy
from app.models.stock import Stock, MarketDataCache

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    回测引擎

    功能：
    1. 执行策略回测
    2. 计算绩效指标
    3. 生成权益曲线
    4. 存储回测结果
    """

    @staticmethod
    async def run_backtest(
        db: AsyncSession,
        config: BacktestConfig,
    ) -> BacktestResult:
        """
        执行回测

        Args:
            db: 数据库会话
            config: 回测配置

        Returns:
            BacktestResult: 回测结果
        """
        start_time = datetime.utcnow()

        # 创建回测结果记录
        result = BacktestResult(
            config_id=config.id,
            user_id=config.user_id,
            status="RUNNING",
            started_at=start_time,
        )
        db.add(result)
        await db.commit()
        await db.refresh(result)

        try:
            # 获取股票列表
            tickers = config.tickers.split(",") if config.tickers else []
            stocks = await BacktestEngine._get_stocks(db, tickers, config.sector, config.market)

            if not stocks:
                raise ValueError("No stocks found for the given criteria")

            # 获取历史数据
            price_data = await BacktestEngine._get_historical_data(
                db, stocks, config.start_date, config.end_date
            )

            if not price_data:
                raise ValueError("No price data found for the backtest period")

            # 执行回测
            trades, equity_curve, daily_values = await BacktestEngine._execute_strategy(
                price_data, config
            )

            # 计算绩效指标
            metrics = BacktestEngine._calculate_metrics(
                trades, equity_curve, daily_values, config.initial_capital, config.commission_rate
            )

            # 更新结果
            result.status = "COMPLETED"
            result.completed_at = datetime.utcnow()
            result.execution_time_seconds = (result.completed_at - start_time).total_seconds()

            # 填充指标
            result.total_return = metrics["total_return"]
            result.annualized_return = metrics["annualized_return"]
            result.max_drawdown = metrics["max_drawdown"]
            result.max_drawdown_duration_days = metrics["max_drawdown_duration_days"]
            result.volatility = metrics["volatility"]
            result.sharpe_ratio = metrics["sharpe_ratio"]
            result.sortino_ratio = metrics["sortino_ratio"]
            result.calmar_ratio = metrics["calmar_ratio"]
            result.total_trades = metrics["total_trades"]
            result.winning_trades = metrics["winning_trades"]
            result.losing_trades = metrics["losing_trades"]
            result.win_rate = metrics["win_rate"]
            result.avg_win_pct = metrics["avg_win_pct"]
            result.avg_loss_pct = metrics["avg_loss_pct"]
            result.profit_factor = metrics["profit_factor"]
            result.avg_holding_period_days = metrics["avg_holding_period_days"]
            result.final_capital = metrics["final_capital"]
            result.total_commission = metrics["total_commission"]

            # 存储详细数据
            result.equity_curve = equity_curve
            result.trades = trades
            result.monthly_returns = BacktestEngine._calculate_monthly_returns(daily_values)

            await db.commit()
            await db.refresh(result)

            logger.info(f"Backtest completed for config {config.id}: {metrics['total_return']:.2%} return")
            return result

        except Exception as e:
            result.status = "FAILED"
            result.error_message = str(e)
            result.completed_at = datetime.utcnow()
            await db.commit()
            logger.error(f"Backtest failed for config {config.id}: {e}")
            raise

    @staticmethod
    async def _get_stocks(
        db: AsyncSession,
        tickers: List[str],
        sector: Optional[str],
        market: Optional[str],
    ) -> List[Stock]:
        """获取符合条件的股票列表"""
        conditions = []

        if tickers:
            conditions.append(Stock.ticker.in_(tickers))
        if sector:
            conditions.append(Stock.sector == sector)
        if market:
            conditions.append(Stock.market == market)

        stmt = select(Stock)
        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def _get_historical_data(
        db: AsyncSession,
        stocks: List[Stock],
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """获取历史价格数据"""
        price_data = {}

        for stock in stocks:
            stmt = select(MarketDataCache).where(
                and_(
                    MarketDataCache.ticker == stock.ticker,
                    MarketDataCache.date >= start_date.date(),
                    MarketDataCache.date <= end_date.date(),
                )
            ).order_by(MarketDataCache.date)

            result = await db.execute(stmt)
            data = result.scalars().all()

            if data:
                price_data[stock.ticker] = [
                    {
                        "date": d.date.isoformat(),
                        "open": float(d.open) if d.open else 0,
                        "high": float(d.high) if d.high else 0,
                        "low": float(d.low) if d.low else 0,
                        "close": float(d.close) if d.close else 0,
                        "volume": int(d.volume) if d.volume else 0,
                    }
                    for d in data
                ]

        return price_data

    @staticmethod
    async def _execute_strategy(
        price_data: Dict[str, List[Dict[str, Any]]],
        config: BacktestConfig,
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        执行策略回测

        简化实现：使用均线交叉策略作为示例
        实际实现应根据 strategy_type 动态选择策略
        """
        trades = []
        equity_curve = []
        daily_values = []

        cash = float(config.initial_capital)
        positions = {}  # {ticker: {"shares": x, "entry_price": y, "entry_date": z}}

        # 解析入场条件
        entry_conditions = config.entry_conditions or {}
        exit_conditions = config.exit_conditions or {}

        # 获取均线参数
        ma_fast = entry_conditions.get("ma_cross", {}).get("fast", 5) if entry_conditions else 5
        ma_slow = entry_conditions.get("ma_cross", {}).get("slow", 20) if entry_conditions else 20
        stop_loss = exit_conditions.get("stop_loss", 0.1) if exit_conditions else 0.1
        take_profit = exit_conditions.get("take_profit", 0.2) if exit_conditions else 0.2

        # 按日期迭代
        all_dates = sorted(set(
            d for data in price_data.values() for d in [pt["date"] for pt in data]
        ))

        position_size_pct = float(config.position_size_pct) / 100.0
        commission_rate = float(config.commission_rate)

        for date_idx, current_date in enumerate(all_dates):
            # 计算均线并生成信号
            for ticker, data in price_data.items():
                # 获取到当前日期的数据
                data_up_to_now = [d for d in data if d["date"] <= current_date]

                if len(data_up_to_now) < ma_slow:
                    continue  # 数据不足，跳过

                closes = [d["close"] for d in data_up_to_now]

                # 计算均线
                ma_fast_val = np.mean(closes[-ma_fast:])
                ma_slow_val = np.mean(closes[-ma_slow:])
                prev_closes = closes[:-1]

                if len(prev_closes) < ma_slow:
                    continue

                prev_ma_fast = np.mean(prev_closes[-ma_fast:])
                prev_ma_slow = np.mean(prev_closes[-ma_slow:])

                current_price = closes[-1]

                # 金叉入场（快线上穿慢线）
                if prev_ma_fast <= prev_ma_slow and ma_fast_val > ma_slow_val:
                    if ticker not in positions and len(positions) < config.max_positions:
                        # 买入
                        shares_to_buy = int((cash * position_size_pct) / current_price)
                        if shares_to_buy > 0:
                            cost = shares_to_buy * current_price * (1 + commission_rate)
                            if cost <= cash:
                                cash -= cost
                                positions[ticker] = {
                                    "shares": shares_to_buy,
                                    "entry_price": current_price,
                                    "entry_date": current_date,
                                }

                # 死叉出场或止损/止盈出场
                elif ticker in positions:
                    pos = positions[ticker]
                    pnl_pct = (current_price - pos["entry_price"]) / pos["entry_price"]

                    # 死叉出场（快线下穿慢线）
                    exit_signal = prev_ma_fast >= prev_ma_slow and ma_fast_val < ma_slow_val

                    # 止损或止盈
                    if pnl_pct <= -stop_loss:
                        exit_signal = True
                    elif pnl_pct >= take_profit:
                        exit_signal = True

                    if exit_signal:
                        # 卖出
                        proceeds = pos["shares"] * current_price * (1 - commission_rate)
                        cash += proceeds
                        trades.append({
                            "ticker": ticker,
                            "entry_date": pos["entry_date"],
                            "exit_date": current_date,
                            "entry_price": pos["entry_price"],
                            "exit_price": current_price,
                            "shares": pos["shares"],
                            "pnl_pct": pnl_pct * 100,
                            "pnl_amount": proceeds - (pos["shares"] * pos["entry_price"]),
                        })
                        del positions[ticker]

            # 计算当日总资产
            total_value = cash
            for ticker, pos in positions.items():
                # 获取当日收盘价
                ticker_data = price_data.get(ticker, [])
                for d in ticker_data:
                    if d["date"] == current_date:
                        total_value += pos["shares"] * d["close"]
                        break

            daily_values.append({
                "date": current_date,
                "value": total_value,
                "cash": cash,
                "positions": len(positions),
            })

        # 平仓所有持仓（按最后一天价格）
        if daily_values and price_data:
            last_date = all_dates[-1]
            for ticker, pos in list(positions.items()):
                ticker_data = price_data.get(ticker, [])
                for d in ticker_data:
                    if d["date"] == last_date:
                        proceeds = pos["shares"] * d["close"] * (1 - commission_rate)
                        cash += proceeds
                        pnl_pct = (d["close"] - pos["entry_price"]) / pos["entry_price"]
                        trades.append({
                            "ticker": ticker,
                            "entry_date": pos["entry_date"],
                            "exit_date": last_date,
                            "entry_price": pos["entry_price"],
                            "exit_price": d["close"],
                            "shares": pos["shares"],
                            "pnl_pct": pnl_pct * 100,
                            "pnl_amount": proceeds - (pos["shares"] * pos["entry_price"]),
                        })
                        break

            total_value = cash
            daily_values[-1]["value"] = total_value

        # 生成权益曲线
        equity_curve = [
            {"date": d["date"], "value": d["value"]}
            for d in daily_values
        ]

        return trades, equity_curve, daily_values

    @staticmethod
    def _calculate_metrics(
        trades: List[Dict],
        equity_curve: List[Dict],
        daily_values: List[Dict],
        initial_capital: float,
        commission_rate: float,
    ) -> Dict[str, Any]:
        """计算绩效指标"""
        if not daily_values or initial_capital <= 0:
            return BacktestEngine._empty_metrics()

        # 基础数据
        values = [d["value"] for d in daily_values]
        final_value = values[-1] if values else initial_capital

        # 总收益
        total_return = (final_value - initial_capital) / initial_capital

        # 年化收益
        days = len(daily_values)
        if days > 0:
            annualized_return = (final_value / initial_capital) ** (252 / days) - 1
        else:
            annualized_return = 0

        # 最大回撤
        peak = values[0]
        max_drawdown = 0
        max_drawdown_duration = 0
        current_drawdown_duration = 0

        for value in values:
            if value > peak:
                peak = value
                current_drawdown_duration = 0
            else:
                drawdown = (peak - value) / peak
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                current_drawdown_duration += 1
                if current_drawdown_duration > max_drawdown_duration:
                    max_drawdown_duration = current_drawdown_duration

        # 波动率（年化）
        if len(values) > 1:
            daily_returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]
            volatility = np.std(daily_returns) * np.sqrt(252)
        else:
            volatility = 0

        # 夏普比率（假设无风险利率 3%）
        risk_free_rate = 0.03
        if volatility > 0:
            sharpe_ratio = (annualized_return - risk_free_rate) / volatility
        else:
            sharpe_ratio = 0

        # 索提诺比率
        if len(values) > 1:
            daily_returns = [(values[i] - values[i-1]) / values[i-1] for i in range(1, len(values))]
            downside_returns = [r for r in daily_returns if r < 0]
            if downside_returns:
                downside_deviation = np.std(downside_returns) * np.sqrt(252)
                sortino_ratio = (annualized_return - risk_free_rate) / downside_deviation if downside_deviation > 0 else 0
            else:
                sortino_ratio = float('inf') if annualized_return > risk_free_rate else 0
        else:
            sortino_ratio = 0

        # 卡玛比率
        calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0

        # 交易统计
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t["pnl_pct"] > 0)
        losing_trades = sum(1 for t in trades if t["pnl_pct"] <= 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        # 平均盈亏
        wins = [t["pnl_pct"] for t in trades if t["pnl_pct"] > 0]
        losses = [t["pnl_pct"] for t in trades if t["pnl_pct"] <= 0]
        avg_win_pct = np.mean(wins) if wins else 0
        avg_loss_pct = np.mean(losses) if losses else 0

        # 盈利因子
        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0

        # 平均持仓天数
        holding_periods = []
        for t in trades:
            try:
                entry = datetime.fromisoformat(t["entry_date"])
                exit = datetime.fromisoformat(t["exit_date"])
                holding_periods.append((exit - entry).days)
            except:
                pass
        avg_holding_period = np.mean(holding_periods) if holding_periods else 0

        # 总手续费（估算）
        total_commission = sum(abs(t.get("pnl_amount", 0)) * commission_rate for t in trades)

        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "max_drawdown": max_drawdown,
            "max_drawdown_duration_days": max_drawdown_duration,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "avg_win_pct": avg_win_pct * 100,  # 转换为百分比
            "avg_loss_pct": avg_loss_pct * 100,
            "profit_factor": profit_factor,
            "avg_holding_period_days": avg_holding_period,
            "final_capital": final_value,
            "total_commission": total_commission,
        }

    @staticmethod
    def _calculate_monthly_returns(daily_values: List[Dict]) -> Dict[str, float]:
        """计算月度收益"""
        if not daily_values:
            return {}

        monthly_values = {}
        for d in daily_values:
            try:
                date = datetime.fromisoformat(d["date"])
                month_key = f"{date.year}-{date.month:02d}"
                monthly_values[month_key] = d["value"]
            except:
                pass

        # 计算月度收益率
        months = sorted(monthly_values.keys())
        monthly_returns = {}

        for i, month in enumerate(months):
            if i == 0:
                continue
            prev_value = monthly_values[months[i-1]]
            curr_value = monthly_values[month]
            monthly_returns[month] = ((curr_value - prev_value) / prev_value) * 100

        return monthly_returns

    @staticmethod
    def _empty_metrics() -> Dict[str, Any]:
        """返回空指标"""
        return {
            "total_return": 0,
            "annualized_return": 0,
            "max_drawdown": 0,
            "max_drawdown_duration_days": 0,
            "volatility": 0,
            "sharpe_ratio": 0,
            "sortino_ratio": 0,
            "calmar_ratio": 0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0,
            "avg_win_pct": 0,
            "avg_loss_pct": 0,
            "profit_factor": 0,
            "avg_holding_period_days": 0,
            "final_capital": 0,
            "total_commission": 0,
        }


# 全局单例
backtest_engine = BacktestEngine()
