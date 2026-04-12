"""
量化因子计算引擎
实现各类因子的计算逻辑
"""
import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from app.models.stock import Stock, MarketDataCache
from app.models.quant_factor import QuantFactor, QuantFactorValue

logger = logging.getLogger(__name__)


class FactorCalculationEngine:
    """
    因子计算引擎

    职责：
    1. 核心量化因子的标准化计算逻辑实现（动量、价值、成长、质量、波动率等）。
    2. 因子处理流程：去极值 (Winsorize) -> 标准化 (Standardize) -> 中性化 (Neutralize)。
    3. 为上层信号生成模块提供底层的数学支撑。
    """

    # ==================== 动量因子 ====================

    @staticmethod
    def momentum_12m(prices: pd.Series, volumes: pd.Series = None) -> pd.Series:
        """
        12 个月动量因子（252 交易日）

        【量化业务逻辑】
        基于“惯性效应”，认为过去表现优异的资产在未来一段时间内仍将保持强势。
        公式：(当前价格 - N日前价格) / N日前价格
        """
        if len(prices) < 253:
            return pd.Series(index=prices.index, dtype=float)

        # 计算 252 个交易日（约一年）的变动率，并乘以 100 转化为百分比
        mom = (prices - prices.shift(252)) / prices.shift(252) * 100
        return mom

    @staticmethod
    def momentum_12m_exclude_1m(prices: pd.Series) -> pd.Series:
        """
        12 个月动量（剔除最近 1 个月）

        【量化业务逻辑】
        由于 A 股市场存在显著的短期反转效应（Short-term Reversal），
        剔除最近 20 或 21 个交易日（1个月）的短期波动，往往能捕捉到更长期的趋势动力。
        公式：(20 日前价格 - 252 日前价格) / 252 日前价格
        """
        if len(prices) < 253:
            return pd.Series(index=prices.index, dtype=float)

        mom = (prices.shift(20) - prices.shift(252)) / prices.shift(252) * 100
        return mom

    @staticmethod
    def momentum_1m(prices: pd.Series) -> pd.Series:
        """
        1 个月动量因子（20 交易日）
        """
        if len(prices) < 21:
            return pd.Series(index=prices.index, dtype=float)

        mom = (prices - prices.shift(20)) / prices.shift(20) * 100
        return mom

    @staticmethod
    def momentum_3m(prices: pd.Series) -> pd.Series:
        """
        3 个月动量因子（60 交易日）
        """
        if len(prices) < 61:
            return pd.Series(index=prices.index, dtype=float)

        mom = (prices - prices.shift(60)) / prices.shift(60) * 100
        return mom

    @staticmethod
    def momentum_6m(prices: pd.Series) -> pd.Series:
        """
        6 个月动量因子（120 交易日）
        """
        if len(prices) < 121:
            return pd.Series(index=prices.index, dtype=float)

        mom = (prices - prices.shift(120)) / prices.shift(120) * 100
        return mom

    # ==================== 价值因子 ====================

    @staticmethod
    def value_pe(pe_ratio: pd.Series) -> pd.Series:
        """
        PE 价值因子

        【量化业务逻辑】
        价值投资的核心：买入便宜的优质资产。
        公式：EP = 1 / PE (Earnings Yield，盈利收益率)。
        之所以求倒数，是为了让“因子值越大”统一代表“价值越高/越便宜”，
        且能更稳健地处理盈利极小的股票，避免 PE 趋于无穷大的计算偏差。
        """
        ep = 1 / pe_ratio
        # 剔除亏损企业（PE <= 0）和数据畸变的极值（PE > 1000）
        ep[(pe_ratio <= 0) | (pe_ratio > 1000)] = np.nan
        return ep * 100  # 转换为百分数

    @staticmethod
    def value_pb(pb_ratio: pd.Series) -> pd.Series:
        """
        PB 价值因子

        公式：BP = 1 / PB（市净率倒数）
        """
        bp = 1 / pb_ratio
        bp[(pb_ratio <= 0) | (pb_ratio > 100)] = np.nan
        return bp * 100

    @staticmethod
    def value_ps(ps_ratio: pd.Series) -> pd.Series:
        """
        PS 价值因子（市销率倒数）
        """
        ps = 1 / ps_ratio
        ps[(ps_ratio <= 0) | (ps_ratio > 100)] = np.nan
        return ps * 100

    @staticmethod
    def value_evp_ebitda(evp_ebitda: pd.Series) -> pd.Series:
        """
        EV/EBITDA 价值因子
        """
        inv = 1 / evp_ebitda
        inv[(evp_ebitda <= 0) | (evp_ebitda > 100)] = np.nan
        return inv * 100

    @staticmethod
    def value_dividend_yield(dividend_yield: pd.Series) -> pd.Series:
        """
        股息率因子
        """
        return dividend_yield

    # ==================== 成长因子 ====================

    @staticmethod
    def growth_revenue(revenue_ttm: pd.Series, revenue_prev: pd.Series) -> pd.Series:
        """
        营收增速因子

        公式：(当期营收 - 上年同期营收) / 上年同期营收
        """
        growth = (revenue_ttm - revenue_prev) / revenue_prev.abs() * 100
        return growth

    @staticmethod
    def growth_earnings(eps_ttm: pd.Series, eps_prev: pd.Series) -> pd.Series:
        """
        盈利增速因子（EPS 增长率）
        """
        growth = (eps_ttm - eps_prev) / eps_prev.abs() * 100
        return growth

    @staticmethod
    def growth_net_profit(npat_ttm: pd.Series, npat_prev: pd.Series) -> pd.Series:
        """
        净利润增速因子
        """
        growth = (npat_ttm - npat_prev) / npat_prev.abs() * 100
        return growth

    @staticmethod
    def growth_roe_chg(roe_curr: pd.Series, roe_prev: pd.Series) -> pd.Series:
        """
        ROE 变化因子
        """
        chg = roe_curr - roe_prev
        return chg

    # ==================== 质量因子 ====================

    @staticmethod
    def quality_roe(roe: pd.Series) -> pd.Series:
        """
        ROE 质量因子
        """
        return roe

    @staticmethod
    def quality_roa(roa: pd.Series) -> pd.Series:
        """
        ROA 质量因子
        """
        return roa

    @staticmethod
    def quality_gross_margin(gross_margin: pd.Series) -> pd.Series:
        """
        毛利率因子
        """
        return gross_margin

    @staticmethod
    def quality_net_margin(net_margin: pd.Series) -> pd.Series:
        """
        净利率因子
        """
        return net_margin

    @staticmethod
    def quality_asset_turnover(asset_turnover: pd.Series) -> pd.Series:
        """
        资产周转率因子
        """
        return asset_turnover

    @staticmethod
    def quality_debt_to_asset(debt_to_asset: pd.Series) -> pd.Series:
        """
        资产负债率因子（逆向，越低越好）
        """
        return -debt_to_asset

    # ==================== 波动率因子 ====================

    @staticmethod
    def volatility_20d(returns: pd.Series) -> pd.Series:
        """
        20 日波动率因子

        【量化业务逻辑】
        波动率往往代表了风险和不确定性。长期证据表明，低波动率股票往往能跑赢高波动率股票（Low-Vol Anomaly）。
        公式：20 日收益率标准差 * sqrt(252)。乘以 252 是为了将日波动率转化为年化波动率。
        """
        if len(returns) < 21:
            return pd.Series(index=returns.index, dtype=float)

        vol = returns.rolling(20).std() * np.sqrt(252) * 100
        return -vol  # 返回负值，因为量化逻辑中通常希望筛选低波动股票（值越大越好）

    @staticmethod
    def volatility_60d(returns: pd.Series) -> pd.Series:
        """
        60 日波动率因子
        """
        if len(returns) < 61:
            return pd.Series(index=returns.index, dtype=float)

        vol = returns.rolling(60).std() * np.sqrt(252) * 100
        return -vol

    @staticmethod
    def downside_deviation(returns: pd.Series, window: int = 252) -> pd.Series:
        """
        下行波动率因子

        只计算负收益的标准差
        """
        def downside_std(x):
            negative = x[x < 0]
            if len(negative) < 2:
                return np.nan
            return negative.std() * np.sqrt(252)

        vol = returns.rolling(window).apply(downside_std, raw=False) * 100
        return -vol

    # ==================== 流动性因子 ====================

    @staticmethod
    def turnover_ratio(volumes: pd.Series, shares_outstanding: pd.Series, window: int = 20) -> pd.Series:
        """
        换手率因子

        公式：20 日平均换手率
        """
        if shares_outstanding is None or len(volumes) < window:
            return pd.Series(index=volumes.index, dtype=float)

        daily_turnover = volumes / shares_outstanding * 100
        avg_turnover = daily_turnover.rolling(window).mean()
        return avg_turnover

    @staticmethod
    def amihud_illiquidity(returns: pd.Series, volumes: pd.Series, window: int = 252) -> pd.Series:
        """
        Amihud 非流动性因子

        公式：|收益率| / 成交额的移动平均
        值越大表示流动性越差（逆向因子）
        """
        if len(returns) < window:
            return pd.Series(index=returns.index, dtype=float)

        illiq = (returns.abs() / volumes).rolling(window).mean() * 1e6
        return -illiq  # 逆向因子

    # ==================== 技术因子 ====================

    @staticmethod
    def rsrs(high: pd.Series, low: pd.Series, close: pd.Series, lookback: int = 17) -> pd.Series:
        """
        RSRS 因子（阻力支撑相对强度）

        【量化业务逻辑】
        这是本项目最高级的技术因子之一，突破了传统指标基于股价绝对位移的限制。
        原理：对一段时期的最高价/最低价进行线性回归，提取斜率 beta。
        - 斜率大：最高价涨得比最低价快，说明阻力在减小，趋势向上态势明确。
        - 波动小：回归的 R-Squared 高则代表支撑/阻力线非常扎实。
        公式：
        1. 对 N 日的高低价做 OLS 回归：High = alpha + beta * Low
        2. RSRS = (beta - mean(beta)) / std(beta)  # 经过标准化后的 Z-Score
        """
        if len(high) < lookback:
            return pd.Series(index=high.index, dtype=float)

        def calc_beta(high_series, low_series):
            if len(high_series) < 5:
                return np.nan
            X = low_series.values
            Y = high_series.values
            X_mean = X.mean()
            Y_mean = Y.mean()
            num = ((X - X_mean) * (Y - Y_mean)).sum()
            den = ((X - X_mean) ** 2).sum()
            if den == 0:
                return np.nan
            return num / den

        # 计算滚动 beta
        betas = []
        for i in range(len(high)):
            if i < lookback - 1:
                betas.append(np.nan)
            else:
                beta = calc_beta(
                    high.iloc[i-lookback+1:i+1],
                    low.iloc[i-lookback+1:i+1]
                )
                betas.append(beta)

        beta_series = pd.Series(betas, index=high.index)

        # 计算 beta 的标准化值
        beta_mean = beta_series.rolling(lookback).mean()
        beta_std = beta_series.rolling(lookback).std()
        rsrs = (beta_series - beta_mean) / beta_std

        return rsrs

    @staticmethod
    def rsi(close: pd.Series, window: int = 14) -> pd.Series:
        """
        RSI 相对强弱指标
        """
        if len(close) < window + 1:
            return pd.Series(index=close.index, dtype=float)

        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)

        avg_gain = gain.rolling(window).mean()
        avg_loss = loss.rolling(window).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def macd_signal(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
        """
        MACD 信号因子

        公式：MACD 线 - Signal 线
        正值表示看涨信号
        """
        if len(close) < slow + signal:
            return pd.Series(index=close.index, dtype=float)

        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()

        macd_signal = macd - signal_line
        return macd_signal

    @staticmethod
    def bollinger_position(close: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.Series:
        """
        布林带位置因子

        公式：(收盘价 - 下轨) / (上轨 - 下轨)
        值在 0-1 之间，表示价格在布林带中的相对位置
        """
        if len(close) < window:
            return pd.Series(index=close.index, dtype=float)

        sma = close.rolling(window).mean()
        std = close.rolling(window).std()
        upper = sma + num_std * std
        lower = sma - num_std * std

        position = (close - lower) / (upper - lower).replace(0, np.nan)
        return position

    # ==================== 工具方法 ====================

    @staticmethod
    def standardize(values: pd.Series, method: str = 'zscore') -> pd.Series:
        """
        因子标准化

        Args:
            values: 因子值序列
            method: 'zscore' 或 'rank'

        Returns:
            标准化后的因子值
        """
        if method == 'zscore':
            mean = values.mean()
            std = values.std()
            if std == 0:
                return pd.Series(0, index=values.index)
            return (values - mean) / std

        elif method == 'rank':
            # 排序归一化到 0-1
            return values.rank(pct=True)

        return values

    @staticmethod
    def winsorize(values: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
        """
        因子去极值（Winsorization）

        Args:
            values: 因子值序列
            lower: 下分位数
            upper: 上分位数

        Returns:
            去极值后的因子值
        """
        lower_bound = values.quantile(lower)
        upper_bound = values.quantile(upper)
        return values.clip(lower_bound, upper_bound)

    @staticmethod
    def neutralize_by_sector(
        factor_values: pd.Series,
        sector_codes: pd.Series,
    ) -> pd.Series:
        """
        行业中性化

        【量化业务逻辑】
        有些因子在某些行业天生偏大（如银行股的 PE 总是很低），为了防止策略过度集中在单一板块，
        我们需要在每个行业内部独立进行标准化，消除由于行业属性带来的误导性偏差。
        """
        df = pd.DataFrame({
            'factor': factor_values,
            'sector': sector_codes
        })

        # 在每个行业组内执行 Z-Score 标准化
        def group_zscore(x):
            if len(x) < 3 or x.std() == 0:
                return pd.Series(0, index=x.index)
            return (x - x.mean()) / x.std()

        neutralized = df.groupby('sector')['factor'].transform(group_zscore)
        return neutralized

    @staticmethod
    def orthogonalize(
        target: pd.Series,
        factors: List[pd.Series],
    ) -> pd.Series:
        """
        因子正交化（施密特正交化）

        去除目标因子与已知因子的相关性

        Args:
            target: 目标因子
            factors: 已知因子列表

        Returns:
            正交化后的残差因子
        """
        # 构建 DataFrame
        df = pd.DataFrame({'target': target})
        for i, f in enumerate(factors):
            df[f'factor_{i}'] = f

        # 删除 NaN
        df = df.dropna()

        if len(df) < len(factors) + 10:
            return pd.Series(index=target.index, dtype=float)

        # 多元回归
        from sklearn.linear_model import LinearRegression

        X = df[[c for c in df.columns if c != 'target']].values
        y = df['target'].values

        model = LinearRegression()
        model.fit(X, y)
        residuals = y - model.predict(X)

        return pd.Series(residuals, index=df.index)


# 全局单例
factor_engine = FactorCalculationEngine()
