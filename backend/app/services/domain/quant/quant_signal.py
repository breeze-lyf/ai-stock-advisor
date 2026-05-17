"""
量化交易信号引擎
基于因子组合生成交易信号
"""
import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func

from app.models.quant_factor import QuantFactor, QuantFactorValue, QuantSignal, QuantStrategy
from app.models.stock import Stock

logger = logging.getLogger(__name__)


class QuantSignalGenerator:
    """
    量化交易信号生成器

    功能：
    1. 多因子综合评分
    2. 信号生成（买入/卖出/持有）
    3. 信号强度计算
    4. 信号持久化
    """

    @staticmethod
    async def generate_signals(
        db: AsyncSession,
        trade_date: date,
        strategy: QuantStrategy,
        stock_pool: Optional[List[str]] = None,
    ) -> List[QuantSignal]:
        """
        生成交易信号

        Args:
            db: 数据库会话
            trade_date: 交易日期
            strategy: 策略配置
            stock_pool: 股票池（可选）

        Returns:
            信号列表
        """
        signals = []

        # 获取因子权重
        factor_weights = strategy.factor_weights or {}
        if not factor_weights:
            logger.warning(f"No factor weights configured for strategy {strategy.id}")
            return signals

        factor_ids = list(factor_weights.keys())

        # 获取当日因子值
        factor_stmt = select(QuantFactorValue).where(
            and_(
                QuantFactorValue.factor_id.in_(factor_ids),
                QuantFactorValue.trade_date == trade_date,
            )
        )
        result = await db.execute(factor_stmt)
        factor_values = result.scalars().all()

        if not factor_values:
            logger.warning(f"No factor values found for date {trade_date}")
            return signals

        # 转换为 DataFrame
        df = pd.DataFrame([{
            'ticker': fv.ticker,
            'factor_id': fv.factor_id,
            'value': fv.zscore_value or fv.rank_value or fv.value,
        } for fv in factor_values])

        if df.empty:
            return signals

        # 股票池过滤
        if stock_pool:
            df = df[df['ticker'].isin(stock_pool)]

        # 【核心逻辑：多因子得分加权】
        # 针对每一只股票，将其所有因子值（通常是经过 Z-Score 标准化的）与其在策略配置中的权重相乘并加总。
        # 结果反映了该股票在当前策略维度下的“综合吸引力”。
        composite_scores = df.groupby('ticker').apply(
            lambda x: sum(x['value'] * factor_weights.get(fid, 0) for fid in factor_ids) / sum(factor_weights.values())
        )

        # 生成信号
        for ticker, score in composite_scores.items():
            # 信号强度归一化到 [-1, 1]
            signal_strength = np.clip(score, -1, 1)

            # 确定信号类型
            if signal_strength > 0.3:
                signal_type = "BUY"
                target_weight = min(signal_strength * strategy.max_position_pct / 100, 1.0)
            elif signal_strength < -0.3:
                signal_type = "SELL"
                target_weight = 0.0
            else:
                signal_type = "HOLD"
                target_weight = None

            # 获取当前价格
            price_stmt = select(func.avg(QuantFactorValue.value)).where(
                and_(
                    QuantFactorValue.ticker == ticker,
                    QuantFactorValue.trade_date == trade_date,
                )
            )
            # 实际需要 join MarketDataCache 获取价格
            # 这里简化处理

            signal = QuantSignal(
                strategy_id=strategy.id,
                ticker=ticker,
                signal_date=trade_date,
                signal_strength=float(signal_strength),
                target_weight=target_weight,
                status="PENDING",
                factor_scores={'composite': float(score)},
            )
            signals.append(signal)

        return signals

    @staticmethod
    async def save_signals(db: AsyncSession, signals: List[QuantSignal]):
        """保存信号到数据库"""
        for signal in signals:
            db.add(signal)
        await db.commit()

    @staticmethod
    async def get_active_signals(
        db: AsyncSession,
        strategy_id: str,
        ticker: Optional[str] = None,
        limit: int = 100,
    ) -> List[QuantSignal]:
        """获取活跃信号"""
        conditions = [
            QuantSignal.strategy_id == strategy_id,
            QuantSignal.status == "PENDING",
        ]
        if ticker:
            conditions.append(QuantSignal.ticker == ticker)

        stmt = select(QuantSignal).where(and_(*conditions)).order_by(
            QuantSignal.signal_date.desc(),
            QuantSignal.signal_strength.desc()
        ).limit(limit)

        result = await db.execute(stmt)
        return result.scalars().all()


class QuantRiskManager:
    """
    量化风险管理引擎

    功能：
    1. 仓位风险监控
    2. 行业暴露控制
    3. 波动率监控
    4. 风险指标计算
    """

    def __init__(
        self,
        max_position_pct: float = 10.0,
        max_sector_exposure: float = 30.0,
        max_portfolio_volatility: float = 20.0,
        var_confidence: float = 0.95,
    ):
        """
        初始化风险管理器

        Args:
            max_position_pct: 单个股最大仓位%
            max_sector_exposure: 最大行业暴露%
            max_portfolio_volatility: 组合最大波动率%
            var_confidence: VaR 置信水平
        """
        self.max_position_pct = max_position_pct
        self.max_sector_exposure = max_sector_exposure
        self.max_portfolio_volatility = max_portfolio_volatility
        self.var_confidence = var_confidence

    def check_position_limits(
        self,
        positions: Dict[str, Dict[str, Any]],
        portfolio_value: float,
    ) -> Dict[str, Any]:
        """
        检查仓位限制

        Args:
            positions: 持仓字典 {ticker: {quantity, price, sector}}
            portfolio_value: 组合总价值

        Returns:
            {"violations": [...], "current_exposure": {...}}
        """
        violations = []
        exposure = {}

        for ticker, pos in positions.items():
            market_value = pos.get('quantity', 0) * pos.get('price', 0)
            if portfolio_value > 0:
                weight = market_value / portfolio_value * 100
            else:
                weight = 0

            exposure[ticker] = {
                'market_value': market_value,
                'weight': round(weight, 2),
            }

            # 检查单个股权重
            if weight > self.max_position_pct:
                violations.append({
                    'type': 'POSITION_LIMIT',
                    'ticker': ticker,
                    'current_weight': weight,
                    'limit': self.max_position_pct,
                })

        # 检查行业暴露
        sector_exposure = {}
        for ticker, pos in positions.items():
            sector = pos.get('sector', 'UNKNOWN')
            market_value = pos.get('quantity', 0) * pos.get('price', 0)
            if portfolio_value > 0:
                sector_weight = market_value / portfolio_value * 100
            else:
                sector_weight = 0

            sector_exposure[sector] = sector_exposure.get(sector, 0) + sector_weight

        for sector, weight in sector_exposure.items():
            if weight > self.max_sector_exposure:
                violations.append({
                    'type': 'SECTOR_LIMIT',
                    'sector': sector,
                    'current_weight': weight,
                    'limit': self.max_sector_exposure,
                })

        exposure['sectors'] = sector_exposure

        return {
            'violations': violations,
            'current_exposure': exposure,
            'compliant': len(violations) == 0,
        }

    def calculate_portfolio_var(
        self,
        returns: pd.Series,
        portfolio_weights: Dict[str, float],
        cov_matrix: pd.DataFrame,
    ) -> float:
        """
        计算组合 VaR（Value at Risk）

        Args:
            returns: 收益率序列
            portfolio_weights: 组合权重
            cov_matrix: 协方差矩阵

        Returns:
            VaR 值（百分比）
        """
        # 【参数法 VaR 计算】
        # 逻辑：基于投资组合的权重分布式和资产间的协方差矩阵，计算组合在特定日期内的潜在最大损失。
        # 公式：Portfolio_Volatility = sqrt(W^T * Cov * W)
        portfolio_vol = np.sqrt(
            np.dot(list(portfolio_weights.values()),
                   np.dot(cov_matrix.values, list(portfolio_weights.values())))
        )

        # 【VaR 转换】
        # 逻辑：利用正态分布分位数（Z-Score）将波动率转化为特定置信水平（如 95%）下的最大可能回撤。
        # 95% 置信水平对应的 z_score 约为 -1.65。
        from scipy.stats import norm
        z_score = norm.ppf(1 - self.var_confidence)

        var = -portfolio_vol * z_score * 100
        return var

    def calculate_risk_metrics(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> Dict[str, float]:
        """
        计算风险指标

        Args:
            returns: 组合收益率序列
            benchmark_returns: 基准收益率序列（可选）

        Returns:
            {volatility, var, beta, tracking_error, ...}
        """
        metrics = {}

        # 年化波动率
        metrics['volatility'] = returns.std() * np.sqrt(252) * 100

        # 下行波动率
        negative_returns = returns[returns < 0]
        if len(negative_returns) > 1:
            metrics['downside_volatility'] = negative_returns.std() * np.sqrt(252) * 100
        else:
            metrics['downside_volatility'] = 0

        # VaR
        metrics['var_95'] = returns.quantile(1 - self.var_confidence) * 100
        metrics['var_99'] = returns.quantile(0.01) * 100

        # Beta（相对于基准）
        if benchmark_returns is not None:
            aligned = pd.DataFrame({
                'portfolio': returns,
                'benchmark': benchmark_returns,
            }).dropna()

            if len(aligned) > 20:
                # Beta（贝塔系数）
                # 逻辑：衡量组合相对于业绩基准的收益波动性。
                # Beta > 1 代表组合比基准更具进攻性；Beta < 1 则更具防御性。
                # 公式：Cov(Rp, Rb) / Var(Rb)
                covariance = aligned['portfolio'].cov(aligned['benchmark'])
                benchmark_var = aligned['benchmark'].var()
                if benchmark_var > 0:
                    metrics['beta'] = covariance / benchmark_var

                # 跟踪误差
                aligned['active_return'] = aligned['portfolio'] - aligned['benchmark']
                metrics['tracking_error'] = aligned['active_return'].std() * np.sqrt(252) * 100

        # 最大回撤
        cumulative = (1 + returns).cumprod()
        cummax = cumulative.cummax()
        drawdown = (cumulative - cummax) / cummax
        metrics['max_drawdown'] = drawdown.min() * 100

        return metrics

    def generate_risk_report(
        self,
        positions: Dict[str, Dict[str, Any]],
        portfolio_value: float,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """
        生成风险报告

        Args:
            positions: 持仓信息
            portfolio_value: 组合价值
            returns: 收益率序列
            benchmark_returns: 基准收益率

        Returns:
            风险报告
        """
        # 仓位检查
        position_check = self.check_position_limits(positions, portfolio_value)

        # 风险指标
        risk_metrics = self.calculate_risk_metrics(returns, benchmark_returns)

        # 风险评级
        risk_level = "LOW"
        if position_check['violations']:
            risk_level = "HIGH"
        elif risk_metrics.get('volatility', 0) > self.max_portfolio_volatility:
            risk_level = "HIGH"
        elif risk_metrics.get('max_drawdown', 0) < -15:
            risk_level = "MEDIUM"

        return {
            'risk_level': risk_level,
            'position_analysis': position_check,
            'risk_metrics': risk_metrics,
            'recommendations': self._generate_recommendations(position_check, risk_metrics),
        }

    def _generate_recommendations(
        self,
        position_check: Dict[str, Any],
        risk_metrics: Dict[str, float],
    ) -> List[str]:
        """生成风险建议"""
        recommendations = []

        for violation in position_check.get('violations', []):
            if violation['type'] == 'POSITION_LIMIT':
                recommendations.append(
                    f"Reduce position in {violation['ticker']} from {violation['current_weight']:.1f}% "
                    f"to {self.max_position_pct:.1f}%"
                )
            elif violation['type'] == 'SECTOR_LIMIT':
                recommendations.append(
                    f"Reduce {violation['sector']} sector exposure from {violation['current_weight']:.1f}% "
                    f"to {self.max_sector_exposure:.1f}%"
                )

        if risk_metrics.get('volatility', 0) > self.max_portfolio_volatility:
            recommendations.append(
                f"Portfolio volatility ({risk_metrics['volatility']:.1f}%) exceeds target "
                f"({self.max_portfolio_volatility}%). Consider adding low-volatility assets."
            )

        if risk_metrics.get('max_drawdown', 0) < -20:
            recommendations.append(
                "Maximum drawdown exceeds 20%. Consider implementing stop-loss or hedging strategies."
            )

        return recommendations


# 全局单例
signal_generator = QuantSignalGenerator()
risk_manager = QuantRiskManager()
