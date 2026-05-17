"""
投资组合优化引擎
实现多种组合优化算法
"""
import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from scipy.optimize import minimize, Bounds, LinearConstraint
from scipy.linalg import sqrtm

logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    """
    投资组合优化器

    支持的优化器类型：
    1. Mean-Variance (均值方差优化)
    2. Black-Litterman (BL 模型)
    3. Risk Parity (风险平价)
    4. Hierarchical Risk Parity (HRP, 层次风险平价)
    5. Minimum Volatility (最小波动率)
    6. Maximum Sharpe (最大夏普比率)
    """

    def __init__(self, risk_free_rate: float = 0.02):
        """
        初始化优化器

        Args:
            risk_free_rate: 无风险利率（年化）
        """
        self.risk_free_rate = risk_free_rate

    # ==================== Mean-Variance 优化 ====================

    def mean_variance_optimization(
        self,
        expected_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        target_return: Optional[float] = None,
        target_volatility: Optional[float] = None,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
        sector_constraints: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        均值方差优化 (Markowitz)

        Args:
            expected_returns: 预期收益率序列
            cov_matrix: 协方差矩阵
            target_return: 目标收益率（可选）
            target_volatility: 目标波动率（可选）
            min_weight: 最小权重
            max_weight: 最大权重
            sector_constraints: 行业约束 {"sector_name": max_pct}

        Returns:
            {"weights": {...}, "expected_return": x, "volatility": x, "sharpe": x}
        """
        n_assets = len(expected_returns)
        assets = expected_returns.index.tolist()
        returns = expected_returns.values
        cov = cov_matrix.values

        # 目标函数：最小化波动率（或最大化夏普）
        def objective(weights):
            portfolio_return = np.sum(weights * returns)
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
            if target_volatility:
                return (portfolio_vol - target_volatility) ** 2
            elif target_return:
                # 给定目标收益下最小化波动率
                return portfolio_vol
            else:
                # 最大化夏普比率
                sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol
                return -sharpe

        # 约束条件
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}  # 权重和为 1
        ]

        if target_return:
            constraints.append({
                'type': 'eq',
                'fun': lambda w: np.dot(w, returns) - target_return
            })

        # 行业约束
        if sector_constraints:
            # 需要外部传入行业映射
            pass  # 简化处理，实际应用需要 sector 映射

        # 权重边界
        bounds = Bounds([min_weight] * n_assets, [max_weight] * n_assets)

        # 初始猜测（等权重）
        x0 = np.array([1.0 / n_assets] * n_assets)

        # 优化
        result = minimize(
            objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000, 'ftol': 1e-10}
        )

        if not result.success:
            logger.warning(f"优化收敛警告：{result.message}")

        weights = result.x
        weights = np.maximum(weights, 0)  # 确保非负
        weights = weights / weights.sum()  # 归一化

        portfolio_return = np.dot(weights, returns)
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0

        return {
            "weights": dict(zip(assets, weights)),
            "expected_return": round(portfolio_return, 6),
            "volatility": round(portfolio_vol, 6),
            "sharpe_ratio": round(sharpe, 4),
            "success": result.success,
        }

    # ==================== Black-Litterman 模型 ====================

    def black_litterman(
        self,
        market_cap: pd.Series,
        cov_matrix: pd.DataFrame,
        views: List[Dict[str, Any]],
        tau: float = 0.05,
        risk_aversion: float = 2.5,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Black-Litterman 模型

        Args:
            market_cap: 市值序列（用于计算市场均衡权重）
            cov_matrix: 协方差矩阵
            views: 观点列表 [{"assets": [...], "view": x, "confidence": y}]
            tau: 先验不确定性参数
            risk_aversion: 风险厌恶系数
            min_weight: 最小权重
            max_weight: 最大权重

        Returns:
            {"weights": {...}, "bl_returns": {...}, "success": bool}
        """
        assets = market_cap.index.tolist()
        n_assets = len(assets)

        # 计算市场权重
        total_cap = market_cap.sum()
        market_weights = (market_cap / total_cap).values

        # 计算均衡预期收益率 (implied equilibrium returns)
        pi = risk_aversion * np.dot(cov_matrix.values, market_weights)

        # 构建观点矩阵 P 和 Q
        n_views = len(views)
        if n_views == 0:
            # 无观点，返回均衡配置
            portfolio_return = np.dot(market_weights, pi)
            portfolio_vol = np.sqrt(np.dot(market_weights.T, np.dot(cov_matrix.values, market_weights)))
            return {
                "weights": dict(zip(assets, market_weights)),
                "bl_returns": dict(zip(assets, pi)),
                "expected_return": round(portfolio_return, 6),
                "volatility": round(portfolio_vol, 6),
            }

        P = np.zeros((n_views, n_assets))
        Q = np.zeros(n_views)
        omega_diag = []

        for i, view in enumerate(views):
            view_assets = view.get('assets', [])
            view_return = view.get('view', 0)
            confidence = view.get('confidence', 0.5)

            for asset in view_assets:
                if asset in assets:
                    idx = assets.index(asset)
                    P[i, idx] = 1.0 / len(view_assets)

            Q[i] = view_return
            # 观点不确定性 (基于 confidence)
            view_variance = (1 - confidence) / confidence * tau * np.dot(
                P[i], np.dot(cov_matrix.values, P[i])
            )
            omega_diag.append(max(view_variance, 1e-6))

        Omega = np.diag(omega_diag)

        # Black-Litterman 公式
        tau_cov = tau * cov_matrix.values

        # M = [(tau * Sigma)^-1 + P' * Omega^-1 * P]^-1
        M = np.linalg.inv(np.linalg.inv(tau_cov) + np.dot(P.T, np.dot(np.linalg.inv(Omega), P)))

        # BL 预期收益率
        bl_returns = np.dot(M, np.dot(np.linalg.inv(tau_cov), pi) + np.dot(P.T, np.dot(np.linalg.inv(Omega), Q)))

        # 使用 BL 收益率进行均值方差优化
        bl_returns_series = pd.Series(bl_returns, index=assets)

        return self.mean_variance_optimization(
            expected_returns=bl_returns_series,
            cov_matrix=cov_matrix,
            min_weight=min_weight,
            max_weight=max_weight,
        )

    # ==================== Risk Parity (风险平价) ====================

    def risk_parity(
        self,
        cov_matrix: pd.DataFrame,
        expected_returns: Optional[pd.Series] = None,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
    ) -> Dict[str, Any]:
        """
        风险平价优化

        每个资产对组合风险的贡献相等

        Args:
            cov_matrix: 协方差矩阵
            expected_returns: 预期收益率（可选）
            min_weight: 最小权重
            max_weight: 最大权重

        Returns:
            {"weights": {...}, "risk_contributions": {...}}
        """
        assets = cov_matrix.index.tolist()
        n_assets = len(assets)
        cov = cov_matrix.values

        # 目标：最小化风险贡献差异
        def objective(weights):
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
            if portfolio_vol < 1e-10:
                return 1e10

            # 边际风险贡献
            marginal_contrib = np.dot(cov, weights) / portfolio_vol
            # 风险贡献
            risk_contrib = weights * marginal_contrib
            # 目标风险贡献（等风险）
            target_risk = portfolio_vol / n_assets
            # 损失：实际风险贡献与目标的差异
            return np.sum((risk_contrib - target_risk) ** 2)

        # 约束
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]

        # 边界
        bounds = Bounds([min_weight] * n_assets, [max_weight] * n_assets)

        # 初始猜测
        x0 = np.array([1.0 / n_assets] * n_assets)

        # 优化
        result = minimize(
            objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000, 'ftol': 1e-12}
        )

        weights = result.x
        weights = np.maximum(weights, 0)
        weights = weights / weights.sum()

        # 计算风险贡献
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
        marginal_contrib = np.dot(cov, weights) / portfolio_vol
        risk_contrib = weights * marginal_contrib

        expected_return = None
        sharpe = None
        if expected_returns is not None:
            expected_return = np.dot(weights, expected_returns.values)
            sharpe = (expected_return - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0

        return {
            "weights": dict(zip(assets, weights)),
            "risk_contributions": dict(zip(assets, risk_contrib)),
            "volatility": round(portfolio_vol, 6),
            "expected_return": round(expected_return, 6) if expected_return else None,
            "sharpe_ratio": round(sharpe, 4) if sharpe else None,
            "success": result.success,
        }

    # ==================== Hierarchical Risk Parity (HRP) ====================

    def hierarchical_risk_parity(
        self,
        returns: pd.DataFrame,
        cov_matrix: Optional[pd.DataFrame] = None,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
    ) -> Dict[str, Any]:
        """
        层次风险平价 (Hierarchical Risk Parity)

        基于聚类分析的资产配置方法

        Args:
            returns: 收益率矩阵 (columns=assets, index=dates)
            cov_matrix: 协方差矩阵（可选，若不提供则从 returns 计算）
            min_weight: 最小权重
            max_weight: 最大权重

        Returns:
            {"weights": {...}, "clusters": [...]}
        """
        from scipy.cluster.hierarchy import linkage, fcluster
        from scipy.spatial.distance import squareform

        assets = returns.columns.tolist()
        n_assets = len(assets)

        if cov_matrix is None:
            cov = returns.cov().values
        else:
            cov = cov_matrix.values

        # 计算相关系数距离矩阵
        corr = np.corrcoef(returns.T)
        # 处理 NaN
        corr = np.nan_to_num(corr, nan=0.0)
        # 确保在 [-1, 1] 范围内
        corr = np.clip(corr, -0.9999, 0.9999)
        # 距离 = sqrt(0.5 * (1 - corr))
        dist = np.sqrt(0.5 * (1 - corr))
        np.fill_diagonal(dist, 0)

        # 层次聚类
        try:
            link = linkage(squareform(dist), method='ward')
        except Exception:
            # ward 可能失败，回退到 average
            link = linkage(squareform(dist), method='average')

        # 获取聚类顺序
        cluster_order = fcluster(link, n_assets, criterion='maxclustmon')

        # 重新排序资产
        sorted_indices = np.argsort(cluster_order)
        sorted_assets = [assets[i] for i in sorted_indices]
        sorted_cov = cov[np.ix_(sorted_indices, sorted_indices)]

        # 自顶向下分配权重
        weights = self._recursive_bisection(sorted_cov, len(sorted_assets))

        # 恢复原始顺序
        final_weights = np.zeros(n_assets)
        for i, orig_idx in enumerate(sorted_indices):
            final_weights[orig_idx] = weights[i]

        # 应用边界约束
        final_weights = np.clip(final_weights, min_weight, max_weight)
        final_weights = final_weights / final_weights.sum()

        # 计算组合指标
        portfolio_vol = np.sqrt(np.dot(final_weights.T, np.dot(cov, final_weights)))
        expected_return = None
        sharpe = None

        if returns is not None:
            mean_returns = returns.mean().values * 252  # 年化
            expected_return = np.dot(final_weights, mean_returns)
            sharpe = (expected_return - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0

        return {
            "weights": dict(zip(assets, final_weights)),
            "volatility": round(portfolio_vol, 6),
            "expected_return": round(expected_return, 6) if expected_return else None,
            "sharpe_ratio": round(sharpe, 4) if sharpe else None,
        }

    def _recursive_bisection(self, cov: np.ndarray, n_assets: int) -> np.ndarray:
        """
        自顶向下双分法权重分配
        """
        weights = np.ones(n_assets)

        # 计算每个资产的方差
        variances = np.diag(cov)

        # 递归分配
        cluster_ids = list(range(n_assets))
        while len(cluster_ids) > 1:
            if len(cluster_ids) % 2 == 1:
                break

            # 成对分配
            new_clusters = []
            for i in range(0, len(cluster_ids), 2):
                c1, c2 = cluster_ids[i], cluster_ids[i + 1]

                # 计算两个聚类的方差
                var1 = np.sum(variances[c1:c2] if isinstance(c1, int) and isinstance(c2, int) else variances[c1])
                var2 = np.sum(variances[c2:c1] if isinstance(c1, int) and isinstance(c2, int) else variances[c2])

                # 逆方差加权
                alpha = 1 - var1 / (var1 + var2) if (var1 + var2) > 0 else 0.5

                weights[c1] *= alpha
                weights[c2] *= (1 - alpha)

                new_clusters.append((c1, c2))

            cluster_ids = [i for pair in new_clusters for i in pair]

        # 归一化
        weights = weights / weights.sum()
        return weights

    # ==================== Minimum Volatility ====================

    def minimum_volatility(
        self,
        cov_matrix: pd.DataFrame,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
    ) -> Dict[str, Any]:
        """
        最小波动率组合
        """
        assets = cov_matrix.index.tolist()
        n_assets = len(assets)
        cov = cov_matrix.values

        def objective(weights):
            return np.sqrt(np.dot(weights.T, np.dot(cov, weights)))

        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        bounds = Bounds([min_weight] * n_assets, [max_weight] * n_assets)
        x0 = np.array([1.0 / n_assets] * n_assets)

        result = minimize(
            objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )

        weights = result.x
        weights = np.maximum(weights, 0)
        weights = weights / weights.sum()

        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))

        return {
            "weights": dict(zip(assets, weights)),
            "volatility": round(portfolio_vol, 6),
            "success": result.success,
        }

    # ==================== Maximum Sharpe ====================

    def maximum_sharpe(
        self,
        expected_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
    ) -> Dict[str, Any]:
        """
        最大夏普比率组合
        """
        assets = expected_returns.index.tolist()
        n_assets = len(assets)
        returns = expected_returns.values
        cov = cov_matrix.values

        def objective(weights):
            portfolio_return = np.dot(weights, returns)
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
            sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol
            return -sharpe

        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        bounds = Bounds([min_weight] * n_assets, [max_weight] * n_assets)
        x0 = np.array([1.0 / n_assets] * n_assets)

        result = minimize(
            objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000}
        )

        weights = result.x
        weights = np.maximum(weights, 0)
        weights = weights / weights.sum()

        portfolio_return = np.dot(weights, returns)
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov, weights)))
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0

        return {
            "weights": dict(zip(assets, weights)),
            "expected_return": round(portfolio_return, 6),
            "volatility": round(portfolio_vol, 6),
            "sharpe_ratio": round(sharpe, 4),
            "success": result.success,
        }


# 全局单例
portfolio_optimizer = PortfolioOptimizer(risk_free_rate=0.02)
