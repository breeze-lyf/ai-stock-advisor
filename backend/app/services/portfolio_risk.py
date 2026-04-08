"""
投资组合风险分析服务
提供风险敞口分析、相关性热力图、再平衡建议、业绩归因等功能
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import math

from app.models.portfolio import Portfolio
from app.models.stock import Stock

logger = logging.getLogger(__name__)


class PortfolioRiskService:
    """
    投资组合风险分析服务

    功能：
    1. 风险敞口分析（行业/地域/市值）
    2. 相关性热力图
    3. 再平衡建议
    4. 业绩归因分析
    """

    # ==================== 风险敞口分析 ====================

    @staticmethod
    async def analyze_sector_exposure(
        db: AsyncSession,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        分析行业风险敞口

        返回：
        {
            "total_value": 100000,
            "sector_breakdown": [
                {"sector": "Technology", "value": 30000, "weight": 0.30},
                {"sector": "Healthcare", "value": 20000, "weight": 0.20},
                ...
            ],
            "concentration_ratio": 0.65,  # 前三大行业集中度
            "herfindahl_index": 0.18,  # 赫芬达尔指数
        }
        """
        # 获取用户持仓
        stmt = select(Portfolio).where(Portfolio.user_id == user_id)
        result = await db.execute(stmt)
        holdings = result.scalars().all()

        if not holdings:
            return {
                "total_value": 0,
                "sector_breakdown": [],
                "concentration_ratio": 0,
                "herfindahl_index": 0,
            }

        # 按行业分组
        sector_values: Dict[str, float] = {}
        total_value = 0

        for holding in holdings:
            if not holding.market_cap or not holding.sector:
                continue

            value = holding.market_cap  # 这里使用 market_cap 作为价值代理
            total_value += value

            if holding.sector not in sector_values:
                sector_values[holding.sector] = 0
            sector_values[holding.sector] += value

        # 计算权重
        sector_breakdown = []
        weights = []

        for sector, value in sorted(sector_values.items(), key=lambda x: x[1], reverse=True):
            weight = value / total_value if total_value > 0 else 0
            sector_breakdown.append({
                "sector": sector,
                "value": round(value, 2),
                "weight": round(weight, 4),
            })
            weights.append(weight)

        # 计算集中度指标
        top_3_weight = sum(weights[:3]) if len(weights) >= 3 else sum(weights)
        herfindahl_index = sum(w ** 2 for w in weights)

        return {
            "total_value": round(total_value, 2),
            "sector_breakdown": sector_breakdown,
            "concentration_ratio": round(top_3_weight, 4),
            "herfindahl_index": round(herfindahl_index, 4),
            "risk_level": "HIGH" if top_3_weight > 0.7 else "MEDIUM" if top_3_weight > 0.5 else "LOW",
        }

    @staticmethod
    async def analyze_market_cap_exposure(
        db: AsyncSession,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        分析市值风格暴露

        返回：
        {
            "large_cap_weight": 0.60,  # 大盘股 (>200 亿)
            "mid_cap_weight": 0.30,    # 中盘股 (50-200 亿)
            "small_cap_weight": 0.10,  # 小盘股 (<50 亿)
            "style_bias": "LARGE_CAP",
        }
        """
        stmt = select(Portfolio).where(Portfolio.user_id == user_id)
        result = await db.execute(stmt)
        holdings = result.scalars().all()

        if not holdings:
            return {
                "large_cap_weight": 0,
                "mid_cap_weight": 0,
                "small_cap_weight": 0,
                "style_bias": "NONE",
            }

        large_cap = 0  # > 200 亿
        mid_cap = 0    # 50-200 亿
        small_cap = 0  # < 50 亿
        total = 0

        for holding in holdings:
            if not holding.market_cap:
                continue

            market_cap = holding.market_cap
            total += market_cap

            if market_cap > 20000000000:  # 200 亿
                large_cap += market_cap
            elif market_cap > 5000000000:  # 50 亿
                mid_cap += market_cap
            else:
                small_cap += market_cap

        if total == 0:
            return {
                "large_cap_weight": 0,
                "mid_cap_weight": 0,
                "small_cap_weight": 0,
                "style_bias": "NONE",
            }

        large_weight = large_cap / total
        mid_weight = mid_cap / total
        small_weight = small_cap / total

        # 判断风格偏好
        if large_weight > 0.6:
            style_bias = "LARGE_CAP"
        elif small_weight > 0.4:
            style_bias = "SMALL_CAP"
        else:
            style_bias = "BALANCED"

        return {
            "large_cap_weight": round(large_weight, 4),
            "mid_cap_weight": round(mid_weight, 4),
            "small_cap_weight": round(small_weight, 4),
            "style_bias": style_bias,
            "large_cap_value": round(large_cap, 2),
            "mid_cap_value": round(mid_cap, 2),
            "small_cap_value": round(small_cap, 2),
        }

    # ==================== 相关性热力图 ====================

    @staticmethod
    async def calculate_correlation_matrix(
        db: AsyncSession,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        计算持仓股票相关性矩阵

        注：实际实现需要获取历史价格数据计算相关系数
        这里提供简化版本

        返回：
        {
            "tickers": ["AAPL", "GOOGL", "MSFT"],
            "correlation_matrix": [
                [1.00, 0.75, 0.68],
                [0.75, 1.00, 0.72],
                [0.68, 0.72, 1.00],
            ],
            "high_correlation_pairs": [
                {"ticker1": "AAPL", "ticker2": "GOOGL", "correlation": 0.75},
            ],
        }
        """
        stmt = select(Portfolio).where(Portfolio.user_id == user_id)
        result = await db.execute(stmt)
        holdings = result.scalars().all()

        if not holdings:
            return {
                "tickers": [],
                "correlation_matrix": [],
                "high_correlation_pairs": [],
            }

        tickers = [h.ticker for h in holdings[:10]]  # 限制最多 10 只股票

        # 简化版本：返回模拟相关性数据
        # 实际实现需要从 MarketDataCache 获取历史价格计算
        n = len(tickers)
        correlation_matrix = []

        for i in range(n):
            row = []
            for j in range(n):
                if i == j:
                    row.append(1.0)
                else:
                    # 模拟相关性：同一行业的股票相关性高
                    holding_i = holdings[i] if i < len(holdings) else None
                    holding_j = holdings[j] if j < len(holdings) else None

                    if holding_i and holding_j and holding_i.sector == holding_j.sector:
                        row.append(0.6 + 0.3 * hash(f"{holding_i.ticker}{holding_j.ticker}") % 100 / 100)
                    else:
                        row.append(0.2 + 0.4 * hash(f"{holding_i.ticker}{holding_j.ticker}") % 100 / 100)
            correlation_matrix.append([round(r, 2) for r in row])

        # 找出高相关性配对
        high_correlation_pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                corr = correlation_matrix[i][j]
                if corr > 0.7:
                    high_correlation_pairs.append({
                        "ticker1": tickers[i],
                        "ticker2": tickers[j],
                        "correlation": round(corr, 2),
                    })

        return {
            "tickers": tickers,
            "correlation_matrix": correlation_matrix,
            "high_correlation_pairs": sorted(high_correlation_pairs, key=lambda x: x["correlation"], reverse=True),
        }

    # ==================== 再平衡建议 ====================

    @staticmethod
    async def generate_rebalance_suggestions(
        db: AsyncSession,
        user_id: str,
        target_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        生成再平衡建议

        Args:
            target_weights: 目标权重配置，如 {"Technology": 0.30, "Healthcare": 0.20}
                            如果不提供，使用等权重作为目标

        返回：
        {
            "current_allocation": [...],
            "target_allocation": [...],
            "deviations": [...],
            "suggestions": [
                {"action": "SELL", "ticker": "AAPL", "current_weight": 0.40, "target_weight": 0.25, "deviation": 0.15},
                {"action": "BUY", "ticker": "GOOGL", "current_weight": 0.10, "target_weight": 0.25, "deviation": -0.15},
            ],
        }
        """
        # 获取当前持仓
        sector_analysis = await PortfolioRiskService.analyze_sector_exposure(db, user_id)

        current_allocation = sector_analysis["sector_breakdown"]

        # 如果不提供目标权重，使用等权重
        if not target_weights:
            n_sectors = len(current_allocation)
            if n_sectors > 0:
                target_weights = {item["sector"]: 1 / n_sectors for item in current_allocation}

        # 计算目标配置
        target_allocation = []
        for sector, weight in sorted(target_weights.items()):
            target_allocation.append({
                "sector": sector,
                "weight": round(weight, 4),
                "value": round(sector_analysis["total_value"] * weight, 2),
            })

        # 计算偏离
        current_weights = {item["sector"]: item["weight"] for item in current_allocation}
        deviations = []
        suggestions = []

        all_sectors = set(current_weights.keys()) | set(target_weights.keys())

        for sector in all_sectors:
            current = current_weights.get(sector, 0)
            target = target_weights.get(sector, 0)
            deviation = current - target

            deviations.append({
                "sector": sector,
                "current_weight": round(current, 4),
                "target_weight": round(target, 4),
                "deviation": round(deviation, 4),
            })

            if abs(deviation) > 0.05:  # 偏离超过 5% 才建议调整
                action = "SELL" if deviation > 0 else "BUY"
                suggestions.append({
                    "sector": sector,
                    "action": action,
                    "current_weight": round(current, 4),
                    "target_weight": round(target, 4),
                    "deviation": round(deviation, 4),
                    "priority": "HIGH" if abs(deviation) > 0.15 else "MEDIUM",
                })

        return {
            "total_value": sector_analysis["total_value"],
            "current_allocation": current_allocation,
            "target_allocation": target_allocation,
            "deviations": sorted(deviations, key=lambda x: abs(x["deviation"]), reverse=True),
            "suggestions": sorted(suggestions, key=lambda x: abs(x["deviation"]), reverse=True),
        }

    # ==================== 业绩归因 ====================

    @staticmethod
    async def analyze_performance_attribution(
        db: AsyncSession,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        业绩归因分析

        将投资收益归因于：
        1. 个股选择效应（Stock Selection）
        2. 行业配置效应（Sector Allocation）
        3. 市场时机效应（Market Timing）

        返回：
        {
            "total_return": 0.15,  # 总收益 15%
            "stock_selection": 0.08,  # 个股选择贡献 8%
            "sector_allocation": 0.05,  # 行业配置贡献 5%
            "market_timing": 0.02,  # 市场时机贡献 2%
            "benchmark_return": 0.10,  # 基准收益 10%
            "alpha": 0.05,  # 超额收益 5%
        }
        """
        stmt = select(Portfolio).where(Portfolio.user_id == user_id)
        result = await db.execute(stmt)
        holdings = result.scalars().all()

        if not holdings:
            return {
                "total_return": 0,
                "stock_selection": 0,
                "sector_allocation": 0,
                "market_timing": 0,
                "benchmark_return": 0,
                "alpha": 0,
            }

        # 简化版本：使用模拟数据
        # 实际实现需要获取历史持仓变化和基准指数数据

        total_value = sum(h.market_cap or 0 for h in holdings)
        total_cost = sum(h.cost_basis or h.market_cap or 0 for h in holdings)

        if total_cost == 0:
            return {
                "total_return": 0,
                "stock_selection": 0,
                "sector_allocation": 0,
                "market_timing": 0,
                "benchmark_return": 0,
                "alpha": 0,
            }

        total_return = (total_value - total_cost) / total_cost

        # 模拟归因分解
        stock_selection = total_return * 0.5  # 假设 50% 来自选股
        sector_allocation = total_return * 0.3  # 30% 来自行业配置
        market_timing = total_return * 0.2  # 20% 来自市场时机

        # 假设基准收益为市场平均回报
        benchmark_return = 0.08  # 8% 基准回报
        alpha = total_return - benchmark_return

        return {
            "total_return": round(total_return, 4),
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "stock_selection": round(stock_selection, 4),
            "sector_allocation": round(sector_allocation, 4),
            "market_timing": round(market_timing, 4),
            "benchmark_return": benchmark_return,
            "alpha": round(alpha, 4),
            "interpretation": PortfolioRiskService._interpret_attribution(
                total_return, stock_selection, sector_allocation, market_timing, alpha
            ),
        }

    @staticmethod
    def _interpret_attribution(
        total_return: float,
        stock_selection: float,
        sector_allocation: float,
        market_timing: float,
        alpha: float,
    ) -> str:
        """解释业绩归因结果"""
        interpretations = []

        if total_return > 0:
            interpretations.append(f"投资组合实现盈利 {total_return:.1%}")
        else:
            interpretations.append(f"投资组合亏损 {total_return:.1%}")

        # 找出主要贡献因素
        contributions = [
            ("个股选择", stock_selection),
            ("行业配置", sector_allocation),
            ("市场时机", market_timing),
        ]
        contributions.sort(key=lambda x: abs(x[1]), reverse=True)

        if contributions[0][1] > 0:
            interpretations.append(f"主要收益来源：{contributions[0][0]}")
        else:
            interpretations.append(f"主要亏损来源：{contributions[0][0]}")

        if alpha > 0:
            interpretations.append(f"跑赢基准 {alpha:.1%}，展现优秀的选股能力")
        elif alpha < 0:
            interpretations.append(f"跑输基准 {abs(alpha):.1%}，需优化投资策略")

        return "；".join(interpretations)


# 全局单例
portfolio_risk_service = PortfolioRiskService()
