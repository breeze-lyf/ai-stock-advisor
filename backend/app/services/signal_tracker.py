"""
AI 信号追踪服务
记录 AI 分析建议，追踪后续表现，计算胜率
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func, update
from sqlalchemy.orm import selectinload

from app.models.ai_signal_history import AISignalHistory, AISignalPerformance, SignalType, SignalStatus
from app.models.analysis import AnalysisReport
from app.models.stock import Stock
from app.services.market_data import MarketDataService

logger = logging.getLogger(__name__)


class SignalTrackerService:
    """
    AI 信号追踪服务

    功能：
    1. 记录 AI 分析生成的信号
    2. 定期更新信号表现
    3. 计算胜率和 performance 统计
    4. 提供信号历史查询
    """

    @staticmethod
    async def create_signal(
        db: AsyncSession,
        user_id: str,
        ticker: str,
        signal_type: SignalType,
        entry_price: float,
        target_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        confidence_score: int = 50,
        time_horizon: str = "SHORT",
        reasoning: Optional[str] = None,
        key_factors: Optional[List[str]] = None,
        analysis_report_id: Optional[str] = None,
    ) -> AISignalHistory:
        """
        创建 AI 信号记录

        Args:
            db: 数据库会话
            user_id: 用户 ID
            ticker: 股票代码
            signal_type: 信号类型
            entry_price: 发布时的价格
            target_price: 目标价
            stop_loss_price: 止损价
            confidence_score: 置信度 (0-100)
            time_horizon: 时间周期 (SHORT/MEDIUM/LONG)
            reasoning: 分析逻辑
            key_factors: 关键因素列表
            analysis_report_id: 关联的分析报告 ID

        Returns:
            AISignalHistory: 创建的信号记录
        """
        signal = AISignalHistory(
            user_id=user_id,
            ticker=ticker,
            signal_type=signal_type,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss_price=stop_loss_price,
            confidence_score=confidence_score,
            time_horizon=time_horizon,
            reasoning=reasoning,
            key_factors=",".join(key_factors) if key_factors else None,
            analysis_report_id=analysis_report_id,
        )
        db.add(signal)
        await db.commit()
        await db.refresh(signal)
        logger.info(f"Signal created: {signal_type.value} {ticker} @ ${entry_price:.2f}")
        return signal

    @staticmethod
    async def update_signal_performance(
        db: AsyncSession,
        signal_id: str,
        current_price: float,
    ) -> Optional[AISignalHistory]:
        """
        更新信号表现（计算浮盈浮亏）

        Args:
            db: 数据库会话
            signal_id: 信号 ID
            current_price: 当前价格

        Returns:
            更新后的信号记录，如果信号不存在则返回 None
        """
        stmt = select(AISignalHistory).where(AISignalHistory.id == signal_id)
        result = await db.execute(stmt)
        signal = result.scalar_one_or_none()

        if not signal or signal.signal_status != SignalStatus.ACTIVE:
            return signal

        # 计算盈亏百分比
        if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            pnl_percent = ((current_price - signal.entry_price) / signal.entry_price) * 100
        else:
            # 做空信号
            pnl_percent = ((signal.entry_price - current_price) / signal.entry_price) * 100

        # 更新最大浮盈和最大回撤
        if pnl_percent > (signal.max_gain or -999):
            signal.max_gain = pnl_percent
        if pnl_percent < (signal.max_drawdown or 999):
            signal.max_drawdown = pnl_percent

        # 检查是否触发止盈或止损
        if signal.target_price and current_price >= signal.target_price:
            signal.signal_status = SignalStatus.CLOSED
            signal.exit_price = signal.target_price
            signal.exit_reason = "TARGET_HIT"
            signal.pnl_percent = pnl_percent
            signal.closed_at = datetime.utcnow()
            logger.info(f"Signal {signal_id} closed: target hit @ ${current_price:.2f}, PnL: {pnl_percent:.2f}%")
        elif signal.stop_loss_price and current_price <= signal.stop_loss_price:
            signal.signal_status = SignalStatus.CLOSED
            signal.exit_price = signal.stop_loss_price
            signal.exit_reason = "STOP_LOSS"
            signal.pnl_percent = pnl_percent
            signal.closed_at = datetime.utcnow()
            logger.info(f"Signal {signal_id} closed: stop loss @ ${current_price:.2f}, PnL: {pnl_percent:.2f}%")

        await db.commit()
        await db.refresh(signal)
        return signal

    @staticmethod
    async def close_signal(
        db: AsyncSession,
        signal_id: str,
        exit_price: float,
        exit_reason: str = "MANUAL",
    ) -> Optional[AISignalHistory]:
        """
        手动关闭信号

        Args:
            db: 数据库会话
            signal_id: 信号 ID
            exit_price: 退出价格
            exit_reason: 退出原因 (MANUAL/TARGET_HIT/STOP_LOSS/TIME_EXPIRED)

        Returns:
            更新后的信号记录
        """
        stmt = select(AISignalHistory).where(AISignalHistory.id == signal_id)
        result = await db.execute(stmt)
        signal = result.scalar_one_or_none()

        if not signal:
            return None

        # 计算盈亏
        if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            pnl_percent = ((exit_price - signal.entry_price) / signal.entry_price) * 100
        else:
            pnl_percent = ((signal.entry_price - exit_price) / signal.entry_price) * 100

        signal.signal_status = SignalStatus.CLOSED
        signal.exit_price = exit_price
        signal.exit_reason = exit_reason
        signal.pnl_percent = pnl_percent
        signal.closed_at = datetime.utcnow()

        db.add(signal)
        await db.commit()
        await db.refresh(signal)
        logger.info(f"Signal {signal_id} manually closed @ ${exit_price:.2f}, PnL: {pnl_percent:.2f}%")
        return signal

    @staticmethod
    async def get_user_signals(
        db: AsyncSession,
        user_id: str,
        ticker: Optional[str] = None,
        status: Optional[SignalStatus] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        获取用户的信号历史

        Args:
            db: 数据库会话
            user_id: 用户 ID
            ticker: 股票代码（可选）
            status: 信号状态（可选）
            limit: 返回数量限制

        Returns:
            信号列表
        """
        conditions = [AISignalHistory.user_id == user_id]

        if ticker:
            conditions.append(AISignalHistory.ticker == ticker)
        if status:
            conditions.append(AISignalHistory.signal_status == status)

        stmt = (
            select(AISignalHistory)
            .where(and_(*conditions))
            .order_by(AISignalHistory.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        signals = result.scalars().all()

        return [SignalTrackerService._signal_to_dict(s) for s in signals]

    @staticmethod
    async def get_user_performance(
        db: AsyncSession,
        user_id: str,
        period: str = "MONTHLY",
    ) -> Dict[str, Any]:
        """
        获取用户的信号表现统计

        Args:
            db: 数据库会话
            user_id: 用户 ID
            period: 统计周期 (DAILY/WEEKLY/MONTHLY/YEARLY/ALL)

        Returns:
            表现统计数据
        """
        # 获取时间范围
        now = datetime.utcnow()
        if period == "DAILY":
            start_date = now - timedelta(days=1)
        elif period == "WEEKLY":
            start_date = now - timedelta(weeks=1)
        elif period == "MONTHLY":
            start_date = now - timedelta(days=30)
        elif period == "YEARLY":
            start_date = now - timedelta(days=365)
        else:  # ALL
            start_date = datetime(2000, 1, 1)

        # 查询信号统计
        stmt = select(
            func.count(AISignalHistory.id).label("total"),
            func.sum(case(AISignalHistory.signal_status == SignalStatus.CLOSED, 1, else_=0)).label("closed"),
            func.sum(case(
                and_(
                    AISignalHistory.signal_status == SignalStatus.CLOSED,
                    AISignalHistory.pnl_percent > 0
                ),
                1,
                else_=0
            )).label("winning"),
            func.sum(case(
                and_(
                    AISignalHistory.signal_status == SignalStatus.CLOSED,
                    AISignalHistory.pnl_percent < 0
                ),
                1,
                else_=0
            )).label("losing"),
            func.avg(AISignalHistory.pnl_percent).label("avg_pnl"),
        ).where(
            and_(
                AISignalHistory.user_id == user_id,
                AISignalHistory.created_at >= start_date
            )
        )
        result = await db.execute(stmt)
        stats = result.first()

        total = stats.total or 0
        closed = stats.closed or 0
        winning = stats.winning or 0
        losing = stats.losing or 0

        win_rate = (winning / closed * 100) if closed > 0 else 0
        avg_pnl = float(stats.avg_pnl or 0)

        # 获取最佳和最差信号
        best_stmt = (
            select(AISignalHistory)
            .where(
                and_(
                    AISignalHistory.user_id == user_id,
                    AISignalHistory.signal_status == SignalStatus.CLOSED,
                    AISignalHistory.pnl_percent > 0
                )
            )
            .order_by(AISignalHistory.pnl_percent.desc())
            .limit(1)
        )
        best_result = await db.execute(best_stmt)
        best_signal = best_result.scalar_one_or_none()

        worst_stmt = (
            select(AISignalHistory)
            .where(
                and_(
                    AISignalHistory.user_id == user_id,
                    AISignalHistory.signal_status == SignalStatus.CLOSED,
                    AISignalHistory.pnl_percent < 0
                )
            )
            .order_by(AISignalHistory.pnl_percent.asc())
            .limit(1)
        )
        worst_result = await db.execute(worst_stmt)
        worst_signal = worst_result.scalar_one_or_none()

        return {
            "period": period,
            "total_signals": total,
            "closed_signals": closed,
            "winning_signals": winning,
            "losing_signals": losing,
            "win_rate": round(win_rate, 2),
            "avg_pnl_percent": round(avg_pnl, 2),
            "best_signal": {
                "ticker": best_signal.ticker if best_signal else None,
                "pnl_percent": float(best_signal.pnl_percent) if best_signal else None,
            },
            "worst_signal": {
                "ticker": worst_signal.ticker if worst_signal else None,
                "pnl_percent": float(worst_signal.pnl_percent) if worst_signal else None,
            },
        }

    @staticmethod
    async def auto_close_expired_signals(
        db: AsyncSession,
        max_age_days: int = 30,
    ) -> int:
        """
        自动关闭过期的信号

        Args:
            db: 数据库会话
            max_age_days: 信号最大有效天数

        Returns:
            关闭的信号数量
        """
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)

        stmt = (
            update(AISignalHistory)
            .where(
                and_(
                    AISignalHistory.signal_status == SignalStatus.ACTIVE,
                    AISignalHistory.created_at < cutoff_date
                )
            )
            .values(
                signal_status=SignalStatus.EXPIRED,
                exit_reason="TIME_EXPIRED",
                updated_at=datetime.utcnow()
            )
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    @staticmethod
    def _signal_to_dict(signal: AISignalHistory) -> Dict[str, Any]:
        """将信号记录转换为字典"""
        return {
            "id": signal.id,
            "ticker": signal.ticker,
            "signal_type": signal.signal_type.value,
            "signal_status": signal.signal_status.value,
            "entry_price": float(signal.entry_price),
            "target_price": float(signal.target_price) if signal.target_price else None,
            "stop_loss_price": float(signal.stop_loss_price) if signal.stop_loss_price else None,
            "confidence_score": signal.confidence_score,
            "time_horizon": signal.time_horizon,
            "reasoning": signal.reasoning,
            "key_factors": signal.key_factors.split(",") if signal.key_factors else [],
            "exit_price": float(signal.exit_price) if signal.exit_price else None,
            "exit_reason": signal.exit_reason,
            "pnl_percent": float(signal.pnl_percent) if signal.pnl_percent else None,
            "max_drawdown": float(signal.max_drawdown) if signal.max_drawdown else None,
            "max_gain": float(signal.max_gain) if signal.max_gain else None,
            "created_at": signal.created_at.isoformat(),
            "closed_at": signal.closed_at.isoformat() if signal.closed_at else None,
        }


# 全局单例
signal_tracker_service = SignalTrackerService()
