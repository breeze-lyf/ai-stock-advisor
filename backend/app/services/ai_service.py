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
        
        # 映射模型 ID (同步最新 SiliconFlow 命名规范: 使用 Qwen3-VL-Thinking)
        model_map = {
            "deepseek-v3": "Pro/deepseek-ai/DeepSeek-V3.2",
            "deepseek-r1": "Pro/deepseek-ai/DeepSeek-R1",
            "qwen-3-vl-thinking": "Qwen/Qwen3-VL-235B-A22B-Thinking",
        }
        # 如果是 qwen 关键字，直接映射到 Qwen3-VL-Thinking
        model_id = model_map.get(model)
        if not model_id:
            if "deepseek" in model: model_id = "Pro/deepseek-ai/DeepSeek-V3.2"
            elif "qwen" in model: model_id = "Qwen/Qwen3-VL-235B-A22B-Thinking"
            else: model_id = "Pro/deepseek-ai/DeepSeek-V3.2"

        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"} if "gemini" not in model else None, # JSON mode
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"SiliconFlow API Error ({response.status_code}): {error_detail}")
                    return f"**Error**: SiliconFlow 调用失败 (HTTP {response.status_code})。详情: {error_detail}"
                
                result = response.json()
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            import traceback
            logger.error(f"SiliconFlow Exception: {str(e)}\n{traceback.format_exc()}")
            return f"**Error**: SiliconFlow 网络异常。{str(e)}"

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
        - **一致性准则 [CRITICAL]**: `immediate_action` 必须与你定义的 `entry_price` 区间严格逻辑一致。
            * 如果 [当前价格] > `entry_price_high`，绝对不能建议“即时买入”或“直接建仓”，而应建议“持筹观望”或“等待回调”。
            * 如果 [当前价格] 处于 [`entry_price_low`, `entry_price_high`] 之间，方可建议“分批买入”或“即刻进场”。
            * 如果 [当前价格] > `target_price`，建议应侧重“分批止盈”或“警惕过热”。
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
            "entry_price_low": "[CRITICAL] 建议买入区间的下限 (Float, 例如：50.50)。必须基于技术支撑位（如布林下轨、MA50、关键支撑位等）。严禁直接使用当前实时价格。",
            "entry_price_high": "[CRITICAL] 建议买入区间的上限 (Float, 例如：52.00)。必须基于技术参考位（如布林中轨、MA20、关键阻力位等）。**严禁等于当前实时价格**——建仓区间应反映技术面上的理想介入范围，而不是'现在就能买到的价格'。",
            "target_price": "预期的止盈位 (Float)。必须基于技术阻力位或布林上轨等。",
            "stop_loss_price": "[CRITICAL] 预期的止损位 (Float)。必须严格低于 entry_price_low (通常建议低 2%-5% 或设在更低一层的关键支撑位)，严禁与建仓下限重叠。",
            "risk_level": "风险等级：低/中/高",
            "investment_horizon": "建议持仓期限",
            "confidence_level": 0-100 (AI 信心指数),
            "technical_analysis": "核心技术位解读（必须分析 RSI, MACD, MA50 等数值）",
            "fundamental_news": "基础面/消息面深度解读",
            "action_advice": "[CRITICAL] 严格按照以下 Markdown 格式生成详细的操作建议，并对关键数值（价格、仓位、止损位）使用 **加粗**：
            
### 1. 交易综述 (Executive Summary)
描述当前市场定性（Context & Trend）和整体建议。例如：当前股价 **$价格** 处于 **[阶段定义]**。建议 **[核心策略]**。

### 2. 结构化操作计划 (Action Plan)
* **首批建仓 (Position 1):** **$建仓位1** (交易触发条件 Trigger，建议仓位 **Position Size**)
* **次批加码 (Position 2):** **$建仓位2** (触发条件及仓位)
* **止损方案 (Stop Loss):** **$止损价** (失效条件 Invalidation：明确说明什么情况下该策略失效)
* **止盈目标 (Target):** **第一目标 $价格**，**第二目标 $价格**。

### 3. 多维逻辑支撑 (Rationale)
* **技术面:** (核心技术指标信号)
* **基本面/情绪面:** (支撑研判的非技术因素)
"
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
