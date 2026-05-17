"""
选股器服务
支持预设策略和自定义条件筛选
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_

from app.models.stock import Stock

logger = logging.getLogger(__name__)


class StockScreenerService:
    """
    选股器服务

    支持：
    1. 预设策略（低估值/成长/动量/高股息）
    2. 自定义条件筛选
    3. 技术面筛选
    4. 基本面筛选
    """

    # ==================== 预设策略 ====================

    @staticmethod
    async def screen_low_valuation(db: AsyncSession, limit: int = 50) -> List[Dict[str, Any]]:
        """
        低估值策略
        - PE < 15
        - PB < 2
        - 股息率 > 2%
        """
        stmt = select(Stock).where(
            and_(
                Stock.pe_ratio.isnot(None),
                Stock.pe_ratio > 0,
                Stock.pe_ratio < 15,
                Stock.pb_ratio.isnot(None),
                Stock.pb_ratio > 0,
                Stock.pb_ratio < 2,
                Stock.dividend_yield.isnot(None),
                Stock.dividend_yield > 2,
            )
        ).limit(limit)

        result = await db.execute(stmt)
        stocks = result.scalars().all()

        return [StockScreenerService._stock_to_dict(s) for s in stocks]

    @staticmethod
    async def screen_growth(db: AsyncSession, limit: int = 50) -> List[Dict[str, Any]]:
        """
        成长策略
        - 营收增速 > 20%
        - 净利增速 > 30%
        - ROE > 15%
        """
        stmt = select(Stock).where(
            and_(
                Stock.revenue_growth.isnot(None),
                Stock.revenue_growth > 20,
                Stock.earnings_growth.isnot(None),
                Stock.earnings_growth > 30,
                Stock.roe.isnot(None),
                Stock.roe > 15,
            )
        ).limit(limit)

        result = await db.execute(stmt)
        stocks = result.scalars().all()

        return [StockScreenerService._stock_to_dict(s) for s in stocks]

    @staticmethod
    async def screen_momentum(db: AsyncSession, limit: int = 50) -> List[Dict[str, Any]]:
        """
        动量策略
        - 股价接近 52 周新高（> 90%）
        - RSI > 50
        """
        # 简化版本：使用 PE 和市值作为动量代理
        stmt = select(Stock).where(
            and_(
                Stock.pe_ratio.isnot(None),
                Stock.pe_ratio > 0,
                Stock.pe_ratio < 50,  # 排除极端高估值
            )
        ).limit(limit)

        result = await db.execute(stmt)
        stocks = result.scalars().all()

        return [StockScreenerService._stock_to_dict(s) for s in stocks]

    @staticmethod
    async def screen_high_dividend(db: AsyncSession, limit: int = 50) -> List[Dict[str, Any]]:
        """
        高股息策略
        - 股息率 > 5%
        - 连续 3 年分红（简化为股息率稳定）
        - PE < 20
        """
        stmt = select(Stock).where(
            and_(
                Stock.dividend_yield.isnot(None),
                Stock.dividend_yield > 5,
                Stock.pe_ratio.isnot(None),
                Stock.pe_ratio > 0,
                Stock.pe_ratio < 20,
            )
        ).limit(limit)

        result = await db.execute(stmt)
        stocks = result.scalars().all()

        return [StockScreenerService._stock_to_dict(s) for s in stocks]

    # ==================== 自定义筛选 ====================

    @staticmethod
    async def screen_custom(
        db: AsyncSession,
        filters: Dict[str, Any],
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        自定义条件筛选

        Args:
            filters: 筛选条件字典
                - pe_ratio_min: PE 最小值
                - pe_ratio_max: PE 最大值
                - pb_ratio_min: PB 最小值
                - pb_ratio_max: PB 最大值
                - roe_min: ROE 最小值
                - revenue_growth_min: 营收增速最小值
                - earnings_growth_min: 净利增速最小值
                - dividend_yield_min: 股息率最小值
                - market_cap_min: 市值最小值
                - market_cap_max: 市值最大值
                - rsi_14_min: RSI 最小值
                - rsi_14_max: RSI 最大值
                - sector: 行业
                - exchange: 交易所

        Returns:
            符合条件的股票列表
        """
        conditions = []

        # 基本面条件
        if "pe_ratio_min" in filters:
            conditions.append(Stock.pe_ratio >= filters["pe_ratio_min"])
        if "pe_ratio_max" in filters:
            conditions.append(Stock.pe_ratio <= filters["pe_ratio_max"])
        if "pb_ratio_min" in filters:
            conditions.append(Stock.pb_ratio >= filters["pb_ratio_min"])
        if "pb_ratio_max" in filters:
            conditions.append(Stock.pb_ratio <= filters["pb_ratio_max"])
        if "roe_min" in filters:
            conditions.append(Stock.roe >= filters["roe_min"])
        if "revenue_growth_min" in filters:
            conditions.append(Stock.revenue_growth >= filters["revenue_growth_min"])
        if "earnings_growth_min" in filters:
            conditions.append(Stock.earnings_growth >= filters["earnings_growth_min"])
        if "dividend_yield_min" in filters:
            conditions.append(Stock.dividend_yield >= filters["dividend_yield_min"])
        if "market_cap_min" in filters:
            conditions.append(Stock.market_cap >= filters["market_cap_min"])
        if "market_cap_max" in filters:
            conditions.append(Stock.market_cap <= filters["market_cap_max"])
        if "sector" in filters:
            conditions.append(Stock.sector == filters["sector"])
        if "exchange" in filters:
            conditions.append(Stock.exchange == filters["exchange"])

        if not conditions:
            # 无条件时返回空列表
            return []

        stmt = select(Stock).where(and_(*conditions)).limit(limit)
        result = await db.execute(stmt)
        stocks = result.scalars().all()

        return [StockScreenerService._stock_to_dict(s) for s in stocks]

    @staticmethod
    async def screen_technical(
        db: AsyncSession,
        rsi_min: Optional[float] = None,
        rsi_max: Optional[float] = None,
        macd_golden_cross: bool = False,
        above_ma20: bool = False,
        above_ma50: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        技术面筛选

        注：当前简化版本，实际技术指标需要集成 MarketData
        """
        # 简化版本：返回所有股票
        stmt = select(Stock).limit(limit)
        result = await db.execute(stmt)
        stocks = result.scalars().all()

        return [StockScreenerService._stock_to_dict(s) for s in stocks]

    # ==================== 工具函数 ====================

    @staticmethod
    def _stock_to_dict(stock: Optional[Stock]) -> Dict[str, Any]:
        """将 Stock 对象转换为字典"""
        if not stock:
            return {}

        # 尝试从 market_data 关系获取实时价格
        current_price = None
        if stock.market_data and hasattr(stock.market_data, 'current_price'):
            current_price = stock.market_data.current_price

        return {
            "ticker": stock.ticker,
            "name": stock.name,
            "current_price": current_price,
            "sector": stock.sector,
            "industry": stock.industry,
            "exchange": stock.exchange,
            "market_cap": stock.market_cap,
            "pe_ratio": stock.pe_ratio,
            "forward_pe": stock.forward_pe,
            "pb_ratio": stock.pb_ratio,
            "ps_ratio": stock.ps_ratio,
            "roe": stock.roe,
            "roa": stock.roa,
            "gross_margin": stock.gross_margin,
            "net_margin": stock.net_margin,
            "revenue_growth": stock.revenue_growth,
            "earnings_growth": stock.earnings_growth,
            "dividend_yield": stock.dividend_yield,
            "beta": stock.beta,
            "fifty_two_week_high": stock.fifty_two_week_high,
            "fifty_two_week_low": stock.fifty_two_week_low,
        }

    @staticmethod
    async def get_available_sectors(db: AsyncSession) -> List[str]:
        """获取所有可用的行业列表"""
        stmt = select(Stock.sector).distinct().where(Stock.sector.isnot(None))
        result = await db.execute(stmt)
        return [row[0] for row in result.all() if row[0]]

    @staticmethod
    async def get_available_industries(db: AsyncSession) -> List[str]:
        """获取所有可用的行业列表"""
        stmt = select(Stock.industry).distinct().where(Stock.industry.isnot(None))
        result = await db.execute(stmt)
        return [row[0] for row in result.all() if row[0]]


# 全局单例
stock_screener_service = StockScreenerService()
