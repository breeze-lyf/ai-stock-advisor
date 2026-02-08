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
            "qwen-3-vl-thinking": "Qwen/Qwen3-VL-235B-A22B-Thinking",
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
    async def generate_analysis(ticker: str, market_data: dict, portfolio_data: dict, news_data: list = None, fundamental_data: dict = None, model: str = "gemini-1.5-flash", api_key_gemini: str = None, api_key_siliconflow: str = None) -> str:
        """
        生成股票投资分析报告
        - 支持 Gemini 和 SiliconFlow (DeepSeek/Qwen)
        """
        # 构建 Prompt
        prompt = f"""
        你是一位资深美股投资顾问和量化策略专家。请基于以下多维数据为代码 [{ticker}] 提供严谨的诊断。
        
        **1. 基础面概览 (Fundamental Context)**:
        - 行业/板块: {fundamental_data.get('sector')} / {fundamental_data.get('industry')}
        - 市值: {fundamental_data.get('market_cap')}
        - PE (TTM): {fundamental_data.get('pe_ratio')} | Forward PE: {fundamental_data.get('forward_pe')}
        - 52周波动范围: [{fundamental_data.get('fifty_two_week_low')}, {fundamental_data.get('fifty_two_week_high')}]
        - Beta: {fundamental_data.get('beta')}
        
        **2. 用户持仓背景 (Portfolio Context)**:
        - 当前成本价: ${portfolio_data.get('avg_cost', 0)}
        - 持仓数量: {portfolio_data.get('quantity', 0)}
        - 未实现盈亏: ${portfolio_data.get('unrealized_pl', 0)} ({portfolio_data.get('pl_percent', 0)}%)
        
        **3. 实时技术面数据 (Technical Data)**:
        - 当前价格: ${market_data.get('current_price')}
        - 今日涨跌: {market_data.get('change_percent')}%
        - RSI (14): {market_data.get('rsi_14')} | KDJ (K): {market_data.get('k_line')} / (D): {market_data.get('d_line')} / (J): {market_data.get('j_line')}
        - MACD: {market_data.get('macd_val')} (柱状图: {market_data.get('macd_hist')}, 斜率: {market_data.get('macd_hist_slope')})
        - 布林带 (BB): 上轨: {market_data.get('bb_upper')} | 均线: {market_data.get('bb_middle')} | 下轨: {market_data.get('bb_lower')}
        - MA 均线: [20: {market_data.get('ma_20')}, 50: {market_data.get('ma_50')}, 200: {market_data.get('ma_200')}]
        - 趋势强度 (ADX): {market_data.get('adx_14')} | ATR: {market_data.get('atr_14')}
        - 枢轴参考 (Pivots): 阻力位 R1: {market_data.get('resistance_1')} / R2: {market_data.get('resistance_2')} | 支撑位 S1: {market_data.get('support_1')} / S2: {market_data.get('support_2')}
        
        **4. 最新消息面 (Recent News)**:
        {news_data if news_data else "暂无重大相关新闻。"}
        
        **任务 (Core Task)**:
        请执行“逻辑严密”的投资诊断。
        
        **重要准则 (Strict Rules)**:
        - **数据驱动**: 所有的止损位、加仓位和目标价**必须基于上述提供的技术指标或基础面数值**。例如，“止损设在 MA50 ({market_data.get('ma_50')}) 附近”或“参考布林线下轨 ({market_data.get('bb_lower')})”。
        - **严禁乱造**: 不要凭空编造 99.42 之类没有任何参考意义的数字。所有的价格锚点必须在数据中有迹可循。
        - **持仓逻辑**: 如果用户当前持仓为 0，建议应侧重于建仓点位；如果已有持仓且浮盈/浮亏较大，应给出止盈/加码或减仓策略。
        
        **返回格式要求**:
        - 使用简洁、专业的中文。
        - **必须在 `technical_analysis` 中明确引用以下数值**: 当前价格、RSI、MACD、MA50/200 或布林带位点。
        - **严谨精度**: AI 建议中的所有价格数值、指标数值必须**四舍五入保留 2 位小数点**（例如：88.54 而不是 88.544834）。
        - 必须返回严格的 JSON 格式。
        
        结果结构:
        {{
            "sentiment_score": 0-100 (量化评分：0=极度看空, 50=中性, 100=极度看多), 
            "summary_status": "4-6字定调",
            "immediate_action": "针对当下的决策建议 (例如：逢低买入/趋势做多/持仓观望/分批减持)",
            "entry_price_low": "[CRITICAL] 建议买入区间的下限 (Float, 例如：50.50)。必须基于技术位（如布林下轨或支撑位）。",
            "entry_price_high": "[CRITICAL] 建议买入区间的上限 (Float, 例如：52.00)。必须基于技术位。",
            "target_price": "预期的止盈位 (Float)",
            "stop_loss_price": "[CRITICAL] 预期的止损位 (Float)。必须严格低于 entry_price_low (通常建议低 2%-5% 或设在更低一层的关键支撑位)，严禁与建仓下限重叠。",
            "risk_level": "风险等级：低/中/高",
            "investment_horizon": "建议持仓期限",
            "confidence_level": 0-100 (AI 信心指数),
            "rr_ratio": "预估盈亏比",
            "technical_analysis": "核心技术位解读（必须分析 RSI, MACD, MA50 等数值）",
            "fundamental_news": "基础面/消息面深度解读",
            "action_advice": "详细的操作逻辑与仓位控制策略。"
        }}
        """
        # 记录 Prompt 到日志，方便调试分析建议的质量 (Req: user callback)
        logger.info(f"--- AI ANALYSIS PROMPT FOR {ticker} ---\n{prompt}\n--------------------------------------")

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
