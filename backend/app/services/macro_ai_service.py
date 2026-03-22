from __future__ import annotations
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
    async def analyze_radar_topics(news_items, db, api_key_siliconflow: str | None = None):
        """
        [AI 逻辑] 宏观雷达主题深度提炼：
        - 输入：通过搜素或聚合得到的近期新闻。
        - 输出：3 个核心宏观主题，包含逻辑链条、利好/利空标的定位。
        """
        news_context = "\n".join([f"- {item.get('title')}: {item.get('content')[:200]}" for item in news_items])
        
        # 提示词设计：强调“首席分析师”角色及“传导逻辑”
        prompt = f"""
        你是一位全球宏观策略首席分析师。请从以下新闻片段中提炼出当前对全球股市（特别是美股）影响最大的 3 个宏观主题。

        新闻背景:
        {news_context}

        对于每个主题，请执行以下深度分析：
        1. 核心逻辑 (Logic Chain): 事件是如何传导并影响市场的。
        2. 利好标的 (Beneficiaries): 哪些板块、指数或具体美股标的受益，并给出理由。
        3. 利空标的 (Detriments): 哪些板块或标多受损，并给出理由。
        4. 热度评分 (Heat Score): 0-100 评分。

        请严格返回以下 JSON 格式：
        {{
          "topics": [
            {{
              "title": "主题标题",
              "summary": "简短背景总结",
              "heat_score": 85,
              "logic": "逻辑链条描述",
              "beneficiaries": [
                {{"ticker": "代码", "reason": "利好路由"}}
              ],
              "detriments": [
                {{"ticker": "代码", "reason": "利空理由"}}
              ],
              "sources": ["url1", "url2"]
            }}
          ]
        }}
        """

        # 获取有效的 API Key (BYOK 优先级高于系统默认)
        final_api_key = api_key_siliconflow or settings.SILICONFLOW_API_KEY
        if not final_api_key:
            logger.error("No SiliconFlow API key provided for macro update.")
            return []

        # 【量化决策逻辑】调用 AI 进行宏观传导分析：
        # 1. 角色设定：要求 AI 扮演顶级对冲基金策略师。
        # 2. 逻辑闭环：不仅仅列出新闻，更要求 AI 推导出“因为 A 事件 -> 导致 B 板块 -> 影响 C 标的”的逻辑链。
        # 3. 结果量化：输出的热度评分 (Heat Score) 辅助用户快速筛选信息权重。
        ai_response = await AIService.call_siliconflow(
            prompt=prompt,
            api_key=final_api_key,
            model=settings.DEFAULT_AI_MODEL,
            db=db,
        )
        
        # 鲁棒性处理：提取并解析 JSON 数据块
        # 使用正则表达式确保在 AI 输出包含思考过程（Thought）或其他杂质时，仍能精准提取 JSON。
        json_match = re.search(r"(\{.*\})", ai_response, re.DOTALL)
        if not json_match:
            logger.error("Failed to extract JSON from AI macro response")
            return []
        data = json.loads(json_match.group(1))
        
        # 返回结构化的主题列表，供持久化层使用
        return data.get("topics", [])

    @staticmethod
    async def generate_hourly_report(news_items, db):
        """
        [AI 逻辑] 整点精要报告生成：
        - 输入：过去一小时的快讯标题。
        - 输出：带情绪评估和标的影响图谱的 JSON。
        """
        titles = [f"- {item.title or item.content[:50]}" for item in news_items]
        content_for_ai = "\n".join(titles)
        
        # 提示词设计：强调“对冲基金经理”视角及“影响图谱”
        prompt = f"""
        你是一位全球对冲基金首席策略师。以下是过去一小时内发生的财联社新闻汇总：

        {content_for_ai}

        请执行以下深度分析任务：
        1. **【全局综述】**: 用 50-100 字概括本小时最重要的 1-3 件核心驱动事件及整体市场情绪。
        2. **【影响图谱 (Impact Map)】**: 识别这些新闻受影响最直接的 5-10 个标的代码 (Tickers)，并说明其利好/利空逻辑。

        请严格返回以下 JSON 格式：
        {{
          "core_summary": "**【核心综述】**\\n具体内容...",
          "sentiment": "看多/看空/中性",
          "impact_map": {{
            "AAPL": "利好理由...",
            "TSLA": "利空理由..."
          }}
        }}
        """

        ai_response = await AIService.call_siliconflow(
            prompt=prompt,
            model=settings.DEFAULT_AI_MODEL,
            api_key=settings.SILICONFLOW_API_KEY,
            db=db,
        )
        # 【多轮决策支持】AI 总结后的解析步骤：
        # 1. 使用正则表达式匹配 JSON，防止 AI 自言自语或输出 Markdown 代码块。
        # 2. 将全局“核心综述”与具体的“标的影响图谱”分离。
        # 3. 影响图谱 (Impact Map) 的设计初衷是为了实现后续的“持仓穿透”，即通过 Ticker 匹配直接定位用户关注的风险。
        json_match = re.search(r"(\{.*\})", ai_response, re.DOTALL)
        if not json_match:
            return None
        return json.loads(json_match.group(1))
