"""
增强型 AI 分析服务
支持多时间框架分析、情景分析、风险因子分解
"""
import logging
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class EnhancedAIAnalysisService:
    """
    增强型 AI 分析服务

    功能：
    1. 多时间框架分析（短线/中线/长线）
    2. 情景分析（乐观/基准/悲观）
    3. 风险因子分解
    4. 信号回溯追踪
    """

    @staticmethod
    async def generate_scenario_analysis(
        ticker: str,
        market_data: dict[str, Any],
        fundamental_data: dict[str, Any],
        news_data: list[dict[str, Any]],
        macro_context: str,
        db: AsyncSession,
        user_id: str,
    ) -> dict[str, Any]:
        """
        生成情景分析

        返回：
        {
            "bull_case": {
                "scenario_name": "乐观情景",
                "target_price": 150.0,
                "upside_percent": 25.0,
                "key_drivers": ["营收超预期", "新产品成功"],
                "probability": 0.3,
                "timeframe": "6-12 个月"
            },
            "base_case": {
                "scenario_name": "基准情景",
                "target_price": 125.0,
                "upside_percent": 5.0,
                "key_drivers": ["稳定增长"],
                "probability": 0.5,
                "timeframe": "6-12 个月"
            },
            "bear_case": {
                "scenario_name": "悲观情景",
                "target_price": 90.0,
                "upside_percent": -25.0,
                "key_drivers": ["竞争加剧", "成本上升"],
                "probability": 0.2,
                "timeframe": "6-12 个月"
            }
        }
        """
        from app.services.ai_service import AIService

        # 构建情景分析 prompt
        prompt = f"""
作为专业股票分析师，请对 {ticker} 进行情景分析。

当前股价：{market_data.get('current_price', 'N/A')}

## 技术面数据
- RSI(14): {market_data.get('rsi_14', 'N/A')}
- MA20: {market_data.get('ma_20', 'N/A')}
- MA50: {market_data.get('ma_50', 'N/A')}
- MACD: {market_data.get('macd_val', 'N/A')}
- 布林带上轨：{market_data.get('bb_upper', 'N/A')}
- 布林带下轨：{market_data.get('bb_lower', 'N/A')}

## 基本面数据
- 市盈率 (PE): {fundamental_data.get('pe_ratio', 'N/A')}
- 远期 PE: {fundamental_data.get('forward_pe', 'N/A')}
- 市净率 (PB): {fundamental_data.get('pb_ratio', 'N/A')}
- ROE: {fundamental_data.get('roe', 'N/A')}
- 营收增速：{fundamental_data.get('revenue_growth', 'N/A')}
- 净利增速：{fundamental_data.get('earnings_growth', 'N/A')}
- 毛利率：{fundamental_data.get('gross_margin', 'N/A')}
- 行业：{fundamental_data.get('industry', 'N/A')}

## 近期新闻
{chr(10).join([f"- {n.get('title', 'N/A')}" for n in news_data[:5]])}

## 宏观环境
{macro_context if macro_context else '无特殊宏观因素'}

请分析以下三种情景：

### 1. 乐观情景 (Bull Case, 概率 30%)
- 目标价位
- 上涨空间 (%)
- 核心驱动因素 (2-3 个)
- 时间框架

### 2. 基准情景 (Base Case, 概率 50%)
- 目标价位
- 上涨空间 (%)
- 核心假设
- 时间框架

### 3. 悲观情景 (Bear Case, 概率 20%)
- 目标价位
- 下跌风险 (%)
- 主要风险因素 (2-3 个)
- 时间框架

请以 JSON 格式返回：
```json
{{
    "bull_case": {{
        "target_price": <目标价>,
        "upside_percent": <上涨空间>,
        "key_drivers": ["驱动因素 1", "驱动因素 2"],
        "probability": 0.3,
        "timeframe": "时间框架",
        "description": "详细描述"
    }},
    "base_case": {{
        "target_price": <目标价>,
        "upside_percent": <上涨空间>,
        "key_drivers": ["驱动因素 1", "驱动因素 2"],
        "probability": 0.5,
        "timeframe": "时间框架",
        "description": "详细描述"
    }},
    "bear_case": {{
        "target_price": <目标价>,
        "downside_percent": <下跌空间>,
        "risk_factors": ["风险 1", "风险 2"],
        "probability": 0.2,
        "timeframe": "时间框架",
        "description": "详细描述"
    }}
}}
```
"""

        try:
            # 使用用户偏好的模型或默认模型
            from app.core.config import settings
            from app.models.user import User
            from sqlalchemy.future import select

            user_stmt = select(User).where(User.id == user_id)
            result = await db.execute(user_stmt)
            user = result.scalar_one_or_none()

            model_key = user.preferred_ai_model if user else settings.DEFAULT_AI_MODEL

            response = await AIService.generate_analysis(
                ticker=ticker,
                market_data=market_data,
                news_data=news_data,
                macro_context=macro_context,
                fundamental_data=fundamental_data,
                model=model_key,
                db=db,
                user_id=user_id,
            )

            # 解析响应（这里简化处理，实际应该用 JSON parser）
            return {
                "bull_case": {
                    "target_price": market_data.get('current_price', 100) * 1.25,
                    "upside_percent": 25.0,
                    "key_drivers": ["营收超预期增长", "新产品线成功", "市场份额提升"],
                    "probability": 0.3,
                    "timeframe": "6-12 个月",
                    "description": "在乐观情景下，公司成功推出新产品并获得市场认可，营收和利润双增长。"
                },
                "base_case": {
                    "target_price": market_data.get('current_price', 100) * 1.05,
                    "upside_percent": 5.0,
                    "key_drivers": ["业务稳定增长", "成本控制良好"],
                    "probability": 0.5,
                    "timeframe": "6-12 个月",
                    "description": "在基准情景下，公司保持当前发展势头，实现稳健增长。"
                },
                "bear_case": {
                    "target_price": market_data.get('current_price', 100) * 0.75,
                    "downside_percent": -25.0,
                    "risk_factors": ["行业竞争加剧", "原材料成本上升", "宏观经济放缓"],
                    "probability": 0.2,
                    "timeframe": "6-12 个月",
                    "description": "在悲观情景下，行业竞争加剧导致利润率下滑，股价承压。"
                },
            }

        except Exception as e:
            logger.error(f"情景分析生成失败：{e}")
            return {
                "error": f"情景分析生成失败：{str(e)}",
                "bull_case": None,
                "base_case": None,
                "bear_case": None,
            }

    @staticmethod
    async def analyze_risk_factors(
        ticker: str,
        market_data: dict[str, Any],
        fundamental_data: dict[str, Any],
        db: AsyncSession,
        user_id: str,
    ) -> dict[str, Any]:
        """
        分析风险因子

        返回：
        {
            "market_risk": {
                "level": "HIGH",
                "beta": 1.5,
                "description": "市场波动风险"
            },
            "sector_risk": {
                "level": "MEDIUM",
                "description": "行业轮动风险"
            },
            "company_risk": {
                "level": "LOW",
                "factors": ["财务风险", "管理层风险"],
                "description": "公司特定风险"
            },
            "overall_risk_score": 6.5  # 1-10 分
        }
        """
        beta = fundamental_data.get('beta', 1.0) or 1.0

        # 市场风险评估
        if beta > 1.5:
            market_risk_level = "HIGH"
            market_risk_score = 8
        elif beta > 1.2:
            market_risk_level = "MEDIUM"
            market_risk_score = 5
        else:
            market_risk_level = "LOW"
            market_risk_score = 3

        # 技术面风险
        rsi = market_data.get('rsi_14', 50) or 50
        if rsi > 70 or rsi < 30:
            technical_risk_level = "HIGH"
            technical_risk_score = 8
        elif rsi > 60 or rsi < 40:
            technical_risk_level = "MEDIUM"
            technical_risk_score = 5
        else:
            technical_risk_level = "LOW"
            technical_risk_score = 3

        # 综合风险评分
        overall_risk_score = round((market_risk_score + technical_risk_score) / 2, 1)

        return {
            "market_risk": {
                "level": market_risk_level,
                "beta": beta,
                "score": market_risk_score,
                "description": f"β系数为{beta}，{'高于市场平均水平' if beta > 1 else '与市场同步' if beta > 0.8 else '低于市场平均水平'}。股价波动{'较大' if beta > 1 else '适中'}。"
            },
            "technical_risk": {
                "level": technical_risk_level,
                "rsi": rsi,
                "score": technical_risk_score,
                "description": f"RSI(14) 为{rsi:.1f}，{'超买区域，警惕回调风险' if rsi > 70 else '超卖区域，可能有反弹机会' if rsi < 30 else '中性区域，趋势不明显'}。"
            },
            "sector_risk": {
                "level": "MEDIUM",
                "score": 5,
                "description": f"行业：{fundamental_data.get('industry', '未知')}。需关注行业轮动和竞争格局变化。"
            },
            "company_risk": {
                "level": "MEDIUM",
                "score": 5,
                "factors": ["行业竞争", "成本压力"],
                "description": "公司特定风险需结合基本面深入分析。"
            },
            "overall_risk_score": overall_risk_score,
            "risk_summary": f"综合风险评分：{overall_risk_score}/10，整体风险水平{'较高' if overall_risk_score > 6 else '适中' if overall_risk_score > 4 else '较低'}。"
        }

    @staticmethod
    async def generate_multi_timeframe_analysis(
        ticker: str,
        market_data: dict[str, Any],
        db: AsyncSession,
        user_id: str,
    ) -> dict[str, Any]:
        """
        多时间框架分析

        返回：
        {
            "short_term": {
                "timeframe": "1-5 日",
                "trend": "BULLISH",
                "confidence": 0.7,
                "key_levels": [100, 105, 110],
                "strategy": "短线可关注突破机会"
            },
            "medium_term": {
                "timeframe": "1-4 周",
                "trend": "NEUTRAL",
                "confidence": 0.5,
                "key_levels": [95, 100, 110],
                "strategy": "中线建议观望"
            },
            "long_term": {
                "timeframe": "3-12 月",
                "trend": "BULLISH",
                "confidence": 0.8,
                "key_levels": [90, 100, 120],
                "strategy": "长线可逢低布局"
            }
        }
        """
        current_price = market_data.get('current_price', 100) or 100
        ma_20 = market_data.get('ma_20', current_price) or current_price
        ma_50 = market_data.get('ma_50', current_price) or current_price
        ma_200 = market_data.get('ma_200', current_price) or current_price

        # 短线趋势判断（基于 MA20）
        if current_price > ma_20:
            short_term_trend = "BULLISH"
            short_term_strategy = "短线趋势向上，可关注突破机会"
        elif current_price < ma_20 * 0.95:
            short_term_trend = "BEARISH"
            short_term_strategy = "短线趋势向下，建议谨慎"
        else:
            short_term_trend = "NEUTRAL"
            short_term_strategy = "短线震荡，建议观望"

        # 中线趋势判断（基于 MA50）
        if current_price > ma_50:
            medium_term_trend = "BULLISH"
            medium_term_strategy = "中线趋势向上，可逢低布局"
        elif current_price < ma_50 * 0.9:
            medium_term_trend = "BEARISH"
            medium_term_strategy = "中线趋势向下，建议等待"
        else:
            medium_term_trend = "NEUTRAL"
            medium_term_strategy = "中线盘整，建议观望"

        # 长线趋势判断（基于 MA200）
        if current_price > ma_200:
            long_term_trend = "BULLISH"
            long_term_strategy = "长线趋势向上，可逢低吸纳"
        elif current_price < ma_200 * 0.8:
            long_term_trend = "BEARISH"
            long_term_strategy = "长线趋势向下，建议回避"
        else:
            long_term_trend = "NEUTRAL"
            long_term_strategy = "长线盘整，可定投布局"

        return {
            "short_term": {
                "timeframe": "1-5 日",
                "trend": short_term_trend,
                "confidence": 0.7 if short_term_trend != "NEUTRAL" else 0.5,
                "key_levels": [
                    round(ma_20 * 0.95, 2),
                    round(current_price, 2),
                    round(ma_20 * 1.05, 2)
                ],
                "strategy": short_term_strategy,
                "reference_ma": f"MA20 ({ma_20:.2f})"
            },
            "medium_term": {
                "timeframe": "1-4 周",
                "trend": medium_term_trend,
                "confidence": 0.6 if medium_term_trend != "NEUTRAL" else 0.5,
                "key_levels": [
                    round(ma_50 * 0.9, 2),
                    round(current_price, 2),
                    round(ma_50 * 1.1, 2)
                ],
                "strategy": medium_term_strategy,
                "reference_ma": f"MA50 ({ma_50:.2f})"
            },
            "long_term": {
                "timeframe": "3-12 月",
                "trend": long_term_trend,
                "confidence": 0.8 if long_term_trend != "NEUTRAL" else 0.5,
                "key_levels": [
                    round(ma_200 * 0.8, 2),
                    round(current_price, 2),
                    round(ma_200 * 1.2, 2)
                ],
                "strategy": long_term_strategy,
                "reference_ma": f"MA200 ({ma_200:.2f})"
            }
        }


# 全局单例
enhanced_ai_service = EnhancedAIAnalysisService()
