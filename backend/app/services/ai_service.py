import google.generativeai as genai
from app.core.config import settings
import logging
import httpx
import json

# 配置日志
logger = logging.getLogger(__name__)

# AI 分析服务：负责与 LLM (Gemini/SiliconFlow) 交互，生成投资分析建议
class AIService:
    _configured = False

    @classmethod
    def _configure_genai(cls, api_key: str = None):
        """配置 Google Generative AI 会话"""
        key = api_key or settings.GEMINI_API_KEY
        if key:
            genai.configure(api_key=key)
            cls._configured = True
        else:
            logger.warning("GEMINI_API_KEY not found.")

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
        1. 综合分析：结合技术指标（趋势、波动、震荡）和最新的消息面，判断当前股价处于什么状态（底部反转、高位调整、强势拉升等）。
        2. 消息面影响：解读最新的新闻对股价是利好还是利空，是否支撑当前的技术走势。
        3. 操作建议：根据用户的持仓成本，给出具体的 [买入/卖出/持有] 建议，并说明理由。
        
        **要求**:
        - 使用中文回答。
        - 必须严格返回如下 JSON 格式。
        
        结果结构:
        {{
            "technical_analysis": "（技术面深度总结，包含对收盘价与均线/布林带关系的解读）",
            "fundamental_news": "（消息面解读，将最近新闻与公司基本面结合）",
            "action_advice": "（给用户的具体操作建议及风控点）"
        }}
        """

        # 分发逻辑
        if "gemini" in model:
            # 使用 Gemini 供应商
            AIService._configure_genai(api_key_gemini)
            try:
                gen_model = genai.GenerativeModel(model_name='models/gemini-1.5-flash')
                response = await gen_model.generate_content_async(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
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
