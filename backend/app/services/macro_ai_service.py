from __future__ import annotations
import asyncio
import json
import logging
import re

from app.core.config import settings
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)


class MacroAIService:
    """
    【宏观 AI 分析服务 (Macro AI Service)】
    利用大语言模型（如 DeepSeek-V3）对海量新闻进行深度提炼。
    核心能力：
    1. 动态雷达主题生成：将离散新闻聚合成有逻辑的投资主题。
    2. 整点总结：每小时生成全局市场情绪和标的影响映射。
    """

    @staticmethod
    async def _call_ai(prompt: str, db=None, max_tokens: int = 2048) -> str:
      """系统级 AI 调用入口：禁用思考模式以加速响应，适用于摘要类任务。"""
      try:
        return await asyncio.wait_for(
            AIService.generate_text(
                prompt, db,
                max_tokens=max_tokens,
                extra_params={"enable_thinking": False},
            ),
            timeout=90,
        )
      except asyncio.TimeoutError:
        logger.error("Macro AI call exceeded 90s business timeout")
        return ""

    @staticmethod
    async def analyze_radar_topics(news_items, db, api_key_siliconflow: str | None = None):
        """
        [AI 逻辑] 宏观雷达主题深度提炼——三层时间维度架构：

        - immediate (即时催化层，0-4h)：突发事件、数据公布、官员讲话，需当日仓位响应
        - narrative (主题演绎层，1-3d)：板块轮动叙事、财报季趋势、政策预期变化，波段决策参考
        - cycle (周期定位层，1-4w)：利率周期、通胀趋势、美元周期，组合配置比例参考

        同时输出 market_pulse（市场体温计），帮助用户秒懂当前风险环境。
        """
        news_context = "\n".join([
            f"[{item.get('source', '未知')}] {item.get('title', '')}: {item.get('content', '')[:200]}"
            for item in news_items
        ])

        prompt = f"""
你是一位管理超过 500 亿美元 AUM 的顶级对冲基金全球宏观策略主管。
你的职责是将以下来自多个信源的原始新闻，转化为可直接指导交易决策的结构化宏观情报。

数据来源说明：
- [东财/同花顺]：中国视角的全球宏观快讯，A 股关联性强
- [yfinance/SPY|QQQ|^VIX|^TNX]：美股四大核心定价因子的实时动态
- [美联储/CNBC 经济/MarketWatch]：高权威度政策与市场信号

原始新闻：
{news_context}

---
请完成两项分析任务：

【任务一】市场体温计 (market_pulse)
基于 VIX 相关新闻、利率动态和整体情绪，快速标定当前市场环境：
- overall_sentiment: 看多/中性偏多/中性/中性偏空/看空
- risk_level: low/medium/high/extreme
- rates_direction: 上行/稳定/下行
- one_line: 10 字以内的市场体温总结

【任务二】核心宏观主题 (topics)
提炼 4-5 个对股票市场影响最大的宏观主题，严格按三层时间维度分类：

时间层定义：
- "immediate"：0-4 小时内的即时催化事件（突发、数据公布、官员讲话），影响当日仓位
- "narrative"：1-3 天的板块轮动叙事或政策预期演绎，影响波段仓位方向
- "cycle"：1-4 周的宏观周期定位信号（利率周期/通胀趋势/美元强弱），影响组合配置比例

对每个主题：
1. 完整传导链条：事件→货币/财政/情绪机制→板块→具体标的
2. 利好标的：优先给出可交易的具体美股 Ticker + 传导路径
3. 利空标的：具体美股 Ticker + 利空路径
4. 热度评分：0-100，90+ 代表需立即关注的紧急信号

请严格返回以下 JSON（不要有任何前缀或 Markdown 包裹）：
{{
  "market_pulse": {{
    "overall_sentiment": "中性偏空",
    "risk_level": "high",
    "rates_direction": "上行",
    "one_line": "避险情绪升温"
  }},
  "topics": [
    {{
      "title": "主题标题（简洁有力）",
      "summary": "50 字以内的背景总结",
      "time_layer": "immediate",
      "heat_score": 88,
      "logic": "事件→机制→板块→标的 完整传导链",
      "beneficiaries": [
        {{"ticker": "GLD", "reason": "利好传导路径"}}
      ],
      "detriments": [
        {{"ticker": "QQQ", "reason": "利空传导路径"}}
      ],
      "sources": []
    }}
  ]
}}
"""

        ai_response = await MacroAIService._call_ai(prompt, db)

        json_match = re.search(r"(\{.*\})", ai_response, re.DOTALL)
        if not json_match:
            logger.error("Failed to extract JSON from AI macro response")
            return []

        try:
            data = json.loads(json_match.group(1))
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in macro AI response: {e}")
            return []

        # 将 market_pulse 注入到每个 topic，方便下游持久化与前端消费
        market_pulse = data.get("market_pulse", {})
        topics = data.get("topics", [])
        for topic in topics:
            topic["market_pulse"] = market_pulse

        return topics

    @staticmethod
    async def generate_hourly_report(news_items, db):
        """
        [AI 逻辑] 整点精要报告生成：
        - 输入：过去一小时最重要的快讯标题（上限 20 条）。
        - 输出：带情绪评估和标的影响图谱的 JSON。
        """
        recent = news_items[:20]
        titles = [f"- {item.title or item.content[:50]}" for item in recent]
        content_for_ai = "\n".join(titles)

        prompt = f"""你是全球对冲基金策略师。以下是过去一小时的财联社新闻：

{content_for_ai}

请返回 JSON（不要 Markdown 包裹）：
{{
  "core_summary": "**【核心综述】**\\n50 字以内概括最重要的 1-2 件事及市场情绪",
  "sentiment": "看多/看空/中性",
  "impact_map": {{
    "TICKER": "10 字以内利好或利空理由"
  }}
}}
impact_map 只列最直接相关的 3-5 个标的。"""

        ai_response = await MacroAIService._call_ai(prompt, db, max_tokens=1024)
        json_match = re.search(r"(\{.*\})", ai_response, re.DOTALL)
        if not json_match:
            return None
        return json.loads(json_match.group(1))
