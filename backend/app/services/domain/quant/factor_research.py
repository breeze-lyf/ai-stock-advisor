"""
因子研究服务
提供 IC 分析、分层回测、因子评价等功能
"""
import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from app.models.quant_factor import QuantFactor, QuantFactorValue, FactorICHistory

logger = logging.getLogger(__name__)


class FactorResearchService:
    """
    因子研究服务

    功能：
    1. IC 分析（Rank IC, Normal IC）
    2. 因子分层回测
    3. 因子自相关性
    4. 因子衰减分析
    5. 因子 IC 历史记录
    """

    @staticmethod
    async def calculate_ic(
        db: AsyncSession,
        factor_id: str,
        start_date: date,
        end_date: date,
        forward_period: int = 5,
        method: str = "rank",
    ) -> Dict[str, Any]:
        """
        计算因子 IC（信息系数）

        Args:
            db: 数据库会话
            factor_id: 因子 ID
            start_date: 开始日期
            end_date: 结束日期
            forward_period: 前瞻期数（默认 5 日）
            method: "rank" 或 "normal"

        Returns:
            {"ic_series": [...], "ic_mean": x, "ic_ir": x, "t_stat": x}
        """
        # 获取因子值
        factor_stmt = select(QuantFactorValue).where(
            and_(
                QuantFactorValue.factor_id == factor_id,
                QuantFactorValue.trade_date >= start_date,
                QuantFactorValue.trade_date <= end_date,
            )
        )
        result = await db.execute(factor_stmt)
        factor_values = result.scalars().all()

        if not factor_values:
            return {"error": "No factor data found"}

        # 转换为 DataFrame
        df = pd.DataFrame([{
            'ticker': fv.ticker,
            'trade_date': fv.trade_date,
            'factor_value': fv.value if fv.value else (fv.zscore_value or fv.rank_value),
        } for fv in factor_values])

        if df.empty:
            return {"error": "No valid factor data"}

        # 获取前瞻收益（需要市场数据服务支持）
        # 这里简化处理，实际需要 join 市场数据
        # forward_returns = await FactorResearchService._get_forward_returns(
        #     db, tickers, dates, forward_period
        # )

        # 简化版 IC 计算（仅示例）
        ic_series = []
        trade_dates = sorted(df['trade_date'].unique())

        for trade_date in trade_dates[:-forward_period]:
            date_df = df[df['trade_date'] == trade_date]
            future_df = df[df['trade_date'] == trade_date + timedelta(days=forward_period)]

            if len(date_df) < 10:
                continue

            # 合并当期因子值和未来收益
            merged = pd.merge(
                date_df[['ticker', 'factor_value']],
                future_df[['ticker', 'factor_value']],
                on='ticker',
                suffixes=('_curr', '_future')
            )

            if len(merged) < 10:
                continue

            if method == "rank":
                ic = merged['factor_value_curr'].rank().corr(
                    merged['factor_value_future'].rank(),
                    method='spearman'
                )
            else:
                ic = merged['factor_value_curr'].corr(
                    merged['factor_value_future'],
                    method='pearson'
                )

            if not np.isnan(ic):
                ic_series.append({
                    'trade_date': trade_date.isoformat(),
                    'ic': ic,
                })

        # 计算统计指标
        ic_values = [x['ic'] for x in ic_series]
        if not ic_values:
            return {"ic_series": [], "ic_mean": 0, "ic_ir": 0}

        ic_mean = np.mean(ic_values)
        ic_std = np.std(ic_values)
        ic_ir = ic_mean / ic_std * np.sqrt(252) if ic_std > 0 else 0

        # T 统计量
        t_stat = ic_mean / (ic_std / np.sqrt(len(ic_values))) if ic_std > 0 else 0

        return {
            "ic_series": ic_series,
            "ic_mean": round(ic_mean, 6),
            "ic_ir": round(ic_ir, 4),
            "t_stat": round(t_stat, 2),
            "sample_size": len(ic_values),
        }

    @staticmethod
    async def calculate_layered_backtest(
        db: AsyncSession,
        factor_id: str,
        start_date: date,
        end_date: date,
        n_layers: int = 10,
    ) -> Dict[str, Any]:
        """
        因子分层回测

        将股票按因子值分为 N 组，计算每组的收益表现

        Args:
            db: 数据库会话
            factor_id: 因子 ID
            start_date: 开始日期
            end_date: 结束日期
            n_layers: 分层数量

        Returns:
            {"equity_curves": {...}, "layer_returns": {...}, "long_short_return": x}
        """
        # 获取因子值
        factor_stmt = select(QuantFactorValue).where(
            and_(
                QuantFactorValue.factor_id == factor_id,
                QuantFactorValue.trade_date >= start_date,
                QuantFactorValue.trade_date <= end_date,
            )
        )
        result = await db.execute(factor_stmt)
        factor_values = result.scalars().all()

        if not factor_values:
            return {"error": "No factor data found"}

        df = pd.DataFrame([{
            'ticker': fv.ticker,
            'trade_date': fv.trade_date,
            'factor_value': fv.zscore_value or fv.rank_value or fv.value,
        } for fv in factor_values])

        if df.empty:
            return {"error": "No valid factor data"}

        # 按日期分组
        trade_dates = sorted(df['trade_date'].unique())
        layer_equity = {f"layer_{i+1}": 1.0 for i in range(n_layers)}
        equity_history = {f"layer_{i+1}": [] for i in range(n_layers)}

        for trade_date in trade_dates[:-1]:
            date_df = df[df['trade_date'] == trade_date]

            if len(date_df) < n_layers:
                continue

            # 按因子值排序并分层
            date_df = date_df.sort_values('factor_value')
            date_df['layer'] = pd.qcut(date_df['factor_value'], n_layers, labels=False, duplicates='drop')

            # 计算每层次日收益（简化处理）
            for layer in range(n_layers):
                layer_stocks = date_df[date_df['layer'] == layer]['ticker'].tolist()

                # 实际应获取这些股票的次日收益
                # 这里简化假设每层收益与因子值正相关
                avg_factor = date_df[date_df['layer'] == layer]['factor_value'].mean()

                # 模拟收益（实际需要 join 市场数据）
                layer_return = avg_factor * 0.01  # 简化转换
                layer_equity[f"layer_{layer+1}"] *= (1 + layer_return)

            # 记录权益
            for k, v in layer_equity.items():
                equity_history[k].append({
                    'date': trade_date.isoformat(),
                    'equity': round(v, 4),
                })

        # 计算多空收益
        long_short_return = layer_equity[f"layer_{n_layers}"] / layer_equity["layer_1"] - 1

        return {
            "equity_curves": equity_history,
            "final_equity": {k: round(v, 4) for k, v in layer_equity.items()},
            "long_short_return": round(long_short_return, 4),
            "layers": n_layers,
        }

    @staticmethod
    async def calculate_factor_turnover(
        db: AsyncSession,
        factor_id: str,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """
        计算因子换手率

        Args:
            db: 数据库会话
            factor_id: 因子 ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            {"avg_turnover": x, "turnover_series": [...]}
        """
        factor_stmt = select(QuantFactorValue).where(
            and_(
                QuantFactorValue.factor_id == factor_id,
                QuantFactorValue.trade_date >= start_date,
                QuantFactorValue.trade_date <= end_date,
            )
        ).order_by(QuantFactorValue.trade_date)

        result = await db.execute(factor_stmt)
        factor_values = result.scalars().all()

        if not factor_values:
            return {"error": "No factor data found"}

        df = pd.DataFrame([{
            'ticker': fv.ticker,
            'trade_date': fv.trade_date,
            'factor_value': fv.zscore_value or fv.rank_value or fv.value,
        } for fv in factor_values])

        # 计算每日排名
        df['rank'] = df.groupby('trade_date')['factor_value'].rank()

        trade_dates = sorted(df['trade_date'].unique())
        turnover_series = []

        for i in range(1, len(trade_dates)):
            prev_date = trade_dates[i - 1]
            curr_date = trade_dates[i]

            prev_df = df[df['trade_date'] == prev_date][['ticker', 'rank']].set_index('ticker')
            curr_df = df[df['trade_date'] == curr_date][['ticker', 'rank']].set_index('ticker')

            # 计算排名变化
            merged = pd.merge(prev_df, curr_df, on='ticker', suffixes=('_prev', '_curr'))
            if len(merged) < 5:
                continue

            # 换手率 = 排名变化绝对值的平均 / (N-1)
            rank_change = (merged['rank_prev'] - merged['rank_curr']).abs()
            turnover = rank_change.mean() / (len(merged) - 1)

            turnover_series.append({
                'date': curr_date.isoformat(),
                'turnover': round(turnover, 4),
            })

        avg_turnover = np.mean([x['turnover'] for x in turnover_series]) if turnover_series else 0

        return {
            "avg_turnover": round(avg_turnover, 4),
            "turnover_series": turnover_series,
        }

    @staticmethod
    async def analyze_factor_decay(
        db: AsyncSession,
        factor_id: str,
        start_date: date,
        end_date: date,
        max_lag: int = 20,
    ) -> Dict[str, Any]:
        """
        因子衰减分析

        计算因子 IC 随滞后期数的变化

        Args:
            db: 数据库会话
            factor_id: 因子 ID
            start_date: 开始日期
            end_date: 结束日期
            max_lag: 最大滞后期

        Returns:
            {"ic_decay": [...], "half_life": x}
        """
        decay_results = []

        for lag in range(1, max_lag + 1):
            ic_result = await FactorResearchService.calculate_ic(
                db, factor_id, start_date, end_date, forward_period=lag
            )

            if 'ic_mean' in ic_result:
                decay_results.append({
                    'lag': lag,
                    'ic_mean': ic_result['ic_mean'],
                })

        # 计算半衰期
        if decay_results:
            initial_ic = decay_results[0]['ic_mean']
            half_ic = initial_ic / 2

            half_life = max_lag
            for r in decay_results:
                if r['ic_mean'] < half_ic:
                    half_life = r['lag']
                    break
        else:
            half_life = 0

        return {
            "ic_decay": decay_results,
            "half_life": half_life,
        }

    @staticmethod
    async def save_ic_history(
        db: AsyncSession,
        factor_id: str,
        ic_data: List[Dict[str, Any]],
        stat_period: str = "DAILY",
    ):
        """
        保存 IC 历史记录到数据库

        Args:
            db: 数据库会话
            factor_id: 因子 ID
            ic_data: IC 数据列表
            stat_period: 统计周期
        """
        for ic_record in ic_data:
            record = FactorICHistory(
                factor_id=factor_id,
                stat_date=datetime.fromisoformat(ic_record['trade_date']),
                stat_period=stat_period,
                ic=ic_record.get('ic'),
                rank_ic=ic_record.get('rank_ic'),
                long_return=ic_record.get('long_return'),
                short_return=ic_record.get('short_return'),
                long_short_return=ic_record.get('long_short_return'),
            )
            db.add(record)

        await db.commit()


# 全局单例
factor_research_service = FactorResearchService()
