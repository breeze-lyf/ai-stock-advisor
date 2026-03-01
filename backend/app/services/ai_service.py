from google import genai
from google.genai import types
from app.core.config import settings
import logging
import httpx
import json

# 配置日志
logger = logging.getLogger(__name__)

# AI 分析服务：负责与 LLM (Gemini/SiliconFlow) 交互，生成投资分析建议
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.ai_config import AIModelConfig
import time
from datetime import datetime

# AI 分析服务 (AI Analysis Service)
# 核心职责：
# 1. 统一封装与不同大模型 (Gemini, 通义千问, DeepSeek) 的对话逻辑。
# 2. 管理并缓存模型配置，避免重复读库。
# 3. 构造极其精准的量化分析提示词 (Prompt)，确保 AI 返回的是可以直接解析的 JSON。
class AIService:
    # --- 性能优化：配置缓存 ---
    # 逻辑：我们将模型配置（如 Provider 是谁、Model ID 是哪个）存在内存里 5 分钟。
    # 这样用户在刷新页面时，不需要每次都由于获取 AI 名字而产生的数据库开销。
    _model_config_cache = {}  
    CACHE_TTL = 300  # 缓存 5 分钟

    @classmethod
    async def get_model_config(cls, model_key: str, db: AsyncSession = None) -> AIModelConfig:
        """
        获取模型配置的阶梯式查找：
        1. 找内存：最快。
        2. 找数据库：如果内存里没有或过期了，去库里翻。
        3. 找兜底：如果库里也没有，用代码里的硬编码常量（防止服务崩溃）。
        """
        # 1. 检查内存缓存
        if model_key in cls._model_config_cache:
            config, timestamp = cls._model_config_cache[model_key]
            if time.time() - timestamp < cls.CACHE_TTL:
                return config

        # 2. 查询数据库
        if db:
            try:
                stmt = select(AIModelConfig).where(AIModelConfig.key == model_key)
                result = await db.execute(stmt)
                config = result.scalar_one_or_none()
                if config:
                    # 写入缓存供下次使用
                    cls._model_config_cache[model_key] = (config, time.time())
                    return config
            except Exception as e:
                logger.error(f"查询 AI 模型配置失败: {e}")

        # 3. 兜底回退：如果数据库也没配，默认指向硅基流动的几个主力模型。
        # 这样即使是刚安装好的应用也能立即开始诊断。
        logger.warning(f"Using fallback config for {model_key} (DB lookup skipped/failed)")
        fallback_map = {
            "deepseek-v3": "Pro/deepseek-ai/DeepSeek-V3.2",
            "deepseek-r1": "Pro/deepseek-ai/DeepSeek-R1",
            "qwen-3-vl-thinking": "Qwen/Qwen3-VL-235B-A22B-Thinking",
            "gemini-1.5-flash": "gemini-1.5-flash"
        }
        # 默认回退到 DeepSeek V3，防止下游 Crash
        fallback_id = fallback_map.get(model_key, "Pro/deepseek-ai/DeepSeek-V3.2")
        return AIModelConfig(key=model_key, provider="siliconflow", model_id=fallback_id)

    @staticmethod
    async def call_siliconflow(prompt: str, model: str, api_key: str, db: AsyncSession = None) -> str:
        """
        硅基流动 (SiliconFlow) 专用调用器：
        它是本项目推荐的国内直连方案，支持 DeepSeek 和 Qwen。
        """
        url = "https://api.siliconflow.cn/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 获取模型在平台上的真实 ID (比如 "Pro/deepseek-ai/DeepSeek-R1")
        config = await AIService.get_model_config(model, db)
        model_id = config.model_id
        
        logger.info(f"Calling SiliconFlow with Model ID: {model_id} (Key: {model})")

        # 构造发给大模型的标准格式 payload
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            # 特别注意：我们强制模型返回 JSON 对象，方便后面解析。
            "response_format": {"type": "json_object"} if "gemini" not in model else None, 
            "stream": False,
            "temperature": 0.3  # 固定低温度，保证分析结果的逻辑性，不要瞎编乱造。
        }
        
        try:
            # 3. 发送异步 HTTP 请求 (Async HTTP Request)
            # 对于国内服务 SiliconFlow，显式禁用系统代理 (trust_env=False)，确保直连稳定性。
            async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                # 4. 错误处理 (Error Handling)
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"SiliconFlow API Error: Status {response.status_code} | Detail: {error_detail}")
                    # 针对特定状态码给出更友好的提示
                    if response.status_code == 401:
                        return "**Error**: AI API Key 无效或已过期。"
                    elif response.status_code == 402:
                        return "**Error**: AI 服务账户余额不足。"
                    elif response.status_code == 429:
                        return "**Error**: AI 接口调用过于频繁，请稍后再试。"
                    return f"**Error**: AI 服务商报错 (HTTP {response.status_code})。"
                
                result = response.json()
                # 提取核心内容
                if "choices" not in result or not result["choices"]:
                    logger.error(f"SiliconFlow Unexpected Response: {result}")
                    return f"**Error**: AI 返回数据格式异常。"
                    
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            import traceback
            logger.error(f"SiliconFlow Exception: {str(e)}\n{traceback.format_exc()}")
            return f"**Error**: AI 连接异常。"


    @staticmethod
    async def generate_analysis(ticker: str, market_data: dict, portfolio_data: dict, news_data: list = None, macro_context: str = None, fundamental_data: dict = None, previous_analysis: dict = None, model: str = "gemini-1.5-flash", api_key_gemini: str = None, api_key_siliconflow: str = None, db: AsyncSession = None) -> str:
        """
        主方法：生成个股深度诊断。
        
        这就是本项目的“灵魂”所在。我们通过极其详细的 Prompt，把股票的：
        1. 价格波动
        2. 指标数值 (RSI/MACD)
        3. 支撑位/阻力位压力
        4. 当前新闻热度
        5. 用户持仓成本
        全部喂给 AI，让它像真人分析师一样给出一个结构化的结论。
        """
        # 构建庞大的 Context (背景板)
        # 告诉 AI 股票的财务情况、盘面情况、甚至用户是不是亏损的（这决定了止损建议的紧迫性）。
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
        
        **4. 实时个股/行业消息面 (Recent Stock News)**:
        {news_data if news_data else "暂无重大相关个股新闻。"}
        
        **5. 全球宏观雷达与热点 (Global Macro Radar & Hotspots)**:
        [CONTEXT]: 以下是当前对全球市场影响最大的热点（已按时间鲜度排序，越靠上越新鲜）。请分析这些最新宏观偏见如何传导至该标的。
        {macro_context if macro_context else "暂无显著全球宏观波动。"}
        
        **6. 历史分析上下文 (Historical Context - Previous AI Analysis)**:
        {f'''
        - 上次分析时间: {previous_analysis.get('time', '未知')}
        - 上次信心及风险: 信心(Confidence): {previous_analysis.get('confidence_level', '无')}/100 | 风险(Risk): {previous_analysis.get('risk_level', '无')}
        - 上次研判结论: {previous_analysis.get('summary_status', '无')} (评分: {previous_analysis.get('sentiment_score', '无')})
        - 上次策略建议: {previous_analysis.get('immediate_action', '无')} (期限: {previous_analysis.get('investment_horizon', '无')})
        - 上次关键点位:
            * 建仓区间: {previous_analysis.get('entry_price_low', '无')} - {previous_analysis.get('entry_price_high', '无')}
            * 止盈目标: {previous_analysis.get('target_price', '无')}
            * 止损红线: {previous_analysis.get('stop_loss_price', '无')}
        - 上次核心观点: {previous_analysis.get('action_advice_short', '无')}...
        [Instruction]: 请参考上述历史观点，根据最新数据微调或不调整。如果市场形势发生重大改变，请明确指出改变原因。
        ''' if previous_analysis else "该股票首次进行 AI 分析，无历史参考数据。"}
        
        **任务 (Core Task)**:
        当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        请执行“逻辑严密”的投资诊断。
        
        **重要准则 (Strict Rules)**:
        - **数据驱动**: 所有的止损位、加仓位和目标价**必须基于上述提供的技术指标或基础面数值**。例如，“止损设在 MA50 ({market_data.get('ma_50')}) 附近”或“参考布林线下轨 ({market_data.get('bb_lower')})”。
        - **一致性准则 [CRITICAL]**: `immediate_action` 必须与你定义的 `entry_price` 区间严格逻辑一致。
            * 如果 [当前价格] > `entry_price_high`，绝对不能建议“即时买入”或“直接建仓”，而应建议“持筹观望”或“等待回调”。
            * 如果 [当前价格] 处于 [`entry_price_low`, `entry_price_high`] 之间，方可建议“分批买入”或“即刻进场”。
            * 如果 [当前价格] > `target_price`，建议应侧重“分批止盈”或“警惕过热”。
        - **严禁乱造**: 不要凭空编造 99.42 之类没有任何参考意义的数字。所有的价格锚点必须在数据中有迹可循。
        - **持仓逻辑**: 如果用户当前持仓为 0，建议应侧重于建仓点位；如果已有持仓且浮盈/浮亏较大，应给出止盈/加码或减仓策略。
        - **仓位管理**: 所有的仓位建议必须基于**总资金的百分比** (例如：5%, 10%)，严禁给出具体的股数 (如：100股)。单只个股总仓位通常不建议超过 20%。
        
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
            
### 1. 建议操作与交易综述
- **建议操作**: **[即时行动建议]**
- **行情综述**: 当前股价 **$价格** 处于 **[阶段定义]**。整体研判为 **[策略定调]**。

### 2. 结构化操作计划
* **首批建仓:** **$建仓位1** (触发条件，建议仓位 **xx%**)
* **次批加码:** **$建仓位2** (触发条件及建议仓位 **xx%**)
* **止损方案:** **$止损价** (失效条件：明确说明什么情况下该策略失效)
* **止盈目标:** **第一目标 $价格**，**第二目标 $价格**。

### 3. 多维逻辑支撑
* **技术面:** (核心技术指标信号)
* **基本面:** (支撑研判的财务因素)
* **消息面/宏观面:** (地缘政治、全球热点或个股重大新闻的传导逻辑)
"
        }}
        """
        # 记录 Prompt 到日志，方便调试分析建议的质量 (Req: user callback)
        logger.info(f"--- AI ANALYSIS PROMPT FOR {ticker} ---\n{prompt}\n--------------------------------------")

        # 分发请求：根据配置去调不同的供应商
        # 获取模型配置，判断 Provider
        model_config = await AIService.get_model_config(model, db)
        provider = model_config.provider
        
        if provider == "gemini":
            # 调 Google 的 Gemini 老家
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
                return f"**Error**: Gemini 解析失败。"
        else:
            key = settings.SILICONFLOW_API_KEY or api_key_siliconflow
            return await AIService.call_siliconflow(prompt, model, key, db)
    @staticmethod
    async def generate_portfolio_analysis(portfolio_items: list, market_news: str = None, macro_context: str = None, model: str = "gemini-1.5-flash", api_key_gemini: str = None, api_key_siliconflow: str = None, db: AsyncSession = None) -> str:
        """
        生成全量持仓健康诊断报告 (Generate Portfolio Health Check)
        """
        if not portfolio_items:
            return json.dumps({"error": "暂无持仓数据"})

        # 构建持仓上下文
        holdings_context = ""
        total_market_value = sum(item.get('market_value', 0) for item in portfolio_items)
        
        for item in portfolio_items:
            weight = (item.get('market_value', 0) / total_market_value * 100) if total_market_value > 0 else 0
            holdings_context += f"- [{item['ticker']}] {item['name']}: 仓位 {weight:.2f}%, 盈亏 {item['pl_percent']:.2f}%, 行业: {item.get('sector', '未知')}\n"

        prompt = f"""
        你是一位资深私人财富管理顾问和首席投资策略师。请对用户的**整个投资组合**进行全面的“全景扫描”与健康诊断。
        
        **1. 持仓明细 (Portfolio Breakdown)**:
        {holdings_context}
        
        **2. 宏观环境与外部背景 (Global Macro & Market Context)**:
        {macro_context if macro_context else "当前无显著宏观热点波动。"}
        
        **3. 补充市场新闻 (Additional News)**:
        {market_news if market_news else "暂无外部实时新闻，请基于已有持仓数据进行存量分析。"}
        
        **4. 分析指令 (Strict Directives)**:
        1. **宏观风险关联**: 必须结合当前的“全球热点”分析其对组合中具体标的的影响（如地缘冲突对能源股、算力脱钩对科技股）。
        2. **深度风险透视**: 不仅要指出行业分布，还要识别“隐性关联”。指出哪个标的对组合的整体风险贡献最大。
        3. **盈亏属性分析**: 分别针对“浮盈巨大”和“严重套牢”的标的给出具体的处理建议。
        4. **调仓战略建议**: 给出未来一周的动作指南。
        5. **禁止空话**: 必须根据数据给出倾向于具体行动的判断。
        
        **返回格式要求**:
        - 必须返回纯 JSON 对象。
        - **详尽报告排版准则 (Layout Rules)**:
            *   使用 `###` 作为一级标题，`####` 作为二级标题。
            *   **必须使用 Markdown 表格**来对比核心数据。
        
        JSON 结构模版:
        {{
            "health_score": 0-100,
            "risk_level": "低/中/高",
            "summary": "核心结论",
            "strategic_advice": "战术动作指南",
            "detailed_report": "深度 Markdown 诊断报告"
        }}
        """

        # 获取模型配置，判断 Provider
        model_config = await AIService.get_model_config(model, db)
        provider = model_config.provider
        
        if provider == "gemini":
            key = api_key_gemini or settings.GEMINI_API_KEY
            if not key: return "**Error**: 缺失 Gemini API Key。"
            try:
                client = genai.Client(api_key=key)
                response = await client.aio.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type='application/json')
                )
                return response.text
            except Exception as e:
                logger.error(f"Portfolio Gemini Error: {str(e)}")
                return json.dumps({"error": f"Gemini 分析失败: {str(e)}"})
        else:
            key = settings.SILICONFLOW_API_KEY or api_key_siliconflow
            return await AIService.call_siliconflow(prompt, model, key, db)
