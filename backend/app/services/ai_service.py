from google import genai
from google.genai import types
from app.core.config import settings
import logging
import httpx
import json

# 配置日志
logger = logging.getLogger(__name__)

# AI 分析服务：负责与 LLM (Gemini/SiliconFlow) 交互，生成投资分析建议
class AIService:
    @staticmethod
    async def _call_siliconflow(prompt: str, model: str, api_key: str) -> str:
        """调用硅基流动 (SiliconFlow) API"""
        url = "https://api.siliconflow.cn/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 映射模型 ID
        model_map = {
            "deepseek-v3": "deepseek-ai/DeepSeek-V3",
            "deepseek-r1": "deepseek-ai/DeepSeek-R1",
            "qwen-2.5-72b": "Qwen/Qwen2.5-72B-Instruct",
            "qwen-3-vl-thinking": "Qwen/Qwen3-VL-8B-Thinking",
        }
        model_id = model_map.get(model, "deepseek-ai/DeepSeek-V3")
        
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"} if "gemini" not in model else None, # JSON mode
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=90.0) as client: # Increased timeout for thinking models
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"SiliconFlow API Error: {str(e)}")
            return f"**Error**: SiliconFlow 调用失败。{str(e)}"

    @staticmethod
    async def generate_analysis(ticker: str, market_data: dict, portfolio_data: dict, news_data: list = None, model: str = "gemini-1.5-flash", api_key_gemini: str = None, api_key_siliconflow: str = None) -> str:
        """
        生成股票投资分析报告
        - 支持 Gemini 和 SiliconFlow (DeepSeek/Qwen)
        """
        # 构建 Prompt
        prompt = f"""
        你是一位资深美股投资顾问。
        
        **用户持仓背景 (Portfolio Context)**:
        - 代码: {ticker}
        - 成本价: ${portfolio_data.get('avg_cost', 0)}
        - 持仓数量: {portfolio_data.get('quantity', 0)}
        - 未实现盈亏: ${portfolio_data.get('unrealized_pl', 0)}
        
        **实时技术面数据 (Technical Data)**:
        - 当前价格: ${market_data.get('current_price')}
        - 今日涨跌: {market_data.get('change_percent')}%
        - RSI (14): {market_data.get('rsi_14')}
        - MACD: {market_data.get('macd_val')} (柱状图: {market_data.get('macd_hist')})
        - 布林带: [{market_data.get('bb_lower')}, {market_data.get('bb_upper')}]
        - KDJ (K): {market_data.get('kdj_k')}
        - ATR: {market_data.get('atr_14')}
        
        **最新消息面 (Recent News)**:
        {news_data if news_data else "暂无重大相关新闻。"}
        
        **任务 (Task)**:
        1. 综合分析：结合技术指标和消息面，给出一个 0-100 的综合评分（0=极度看空，100=极度看多）。
        2. 状态定调：用 4-6 个字总结当前股票状态（如：高位超买、底部反转、横盘蓄势）。
        3. 消息面影响：解读新闻利好/利空。
        4. 操作建议：根据持仓成本给出 [买入/卖出/持有] 建议。
        
        **要求**:
        - 使用中文回答。
        - 必须严格返回如下 JSON 格式。
        
        结果结构:
        {{
            "sentiment_score": 85, 
            "summary_status": "强势突破",
            "risk_level": "中等",
            "technical_analysis": "（技术面解读）",
            "fundamental_news": "（消息面解读）",
            "action_advice": "（给用户的具体操作建议）"
        }}
        """

        # 分发逻辑
        if "gemini" in model:
            # 使用 Gemini 供应商 (新版 google-genai SDK)
            key = api_key_gemini or settings.GEMINI_API_KEY
            if not key:
                return "**Error**: 缺失 Gemini API Key。"
                
            try:
                client = genai.Client(api_key=key)
                # 使用异步客户端进行调用
                response = await client.aio.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json'
                    )
                )
                return response.text
            except Exception as e:
                logger.error(f"Gemini API Error: {str(e)}")
                return f"**Error**: Gemini 分析失败。{str(e)}"
        else:
            # 优先使用系统配置的 API Key
            key = settings.SILICONFLOW_API_KEY or api_key_siliconflow or settings.DEEPSEEK_API_KEY
            if not key:
                return "**Error**: 缺失 SiliconFlow API Key，请联系管理员配置或在设置中心设置。"
            return await AIService._call_siliconflow(prompt, model, key)
