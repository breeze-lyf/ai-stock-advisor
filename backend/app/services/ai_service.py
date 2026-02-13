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

# AI 分析服务 (AI Analysis Service)
# 核心职责 (Core Responsibilities):
# 1. 统一封装与 LLM (Gemini, SiliconFlow/DeepSeek/Qwen) 的交互接口
# 2. 管理 AI 模型配置的动态加载与缓存 (Dynamic Config & Caching)
# 3. 构建专业的量化分析 Prompt，确保输出格式严格符合 JSON 规范
class AIService:
    # --- 配置缓存机制 (Configuration Caching) ---
    # 目的: 减少对数据库的高频读取，提高 API 响应速度
    # 结构: { model_key: (AIModelConfig_Object, timestamp) }
    _model_config_cache = {}  
    CACHE_TTL = 300  # 缓存有效期: 5 分钟 (5 Minutes)

    @classmethod
    async def get_model_config(cls, model_key: str, db: AsyncSession = None) -> AIModelConfig:
        """
        获取 AI 模型配置 (Get AI Model Configuration)
        
        策略 (Strategy): -> L1: Memory Cache -> L2: Database -> L3: Hardcoded Fallback
        
        Args:
            model_key (str): 模型的唯一标识键 (e.g., "deepseek-r1", "gemini-1.5-flash")
            db (AsyncSession, optional): 数据库会话，用于 L2 查询
            
        Returns:
            AIModelConfig: 模型配置对象，包含 provider, model_id 等关键信息
        """
        # 1. Level 1: 检查内存缓存 (Check Memory Cache)
        if model_key in cls._model_config_cache:
            config, timestamp = cls._model_config_cache[model_key]
            # 检查 TTL 是否过期
            if time.time() - timestamp < cls.CACHE_TTL:
                return config

        # 2. Level 2: 查询数据库 (Check Database)
        if db:
            try:
                stmt = select(AIModelConfig).where(AIModelConfig.key == model_key)
                result = await db.execute(stmt)
                config = result.scalar_one_or_none()
                if config:
                    # 写入缓存 (Write-back to cache)
                    cls._model_config_cache[model_key] = (config, time.time())
                    return config
            except Exception as e:
                logger.error(f"Error fetching AI model config for {model_key}: {e}")

        # 3. Level 3: 兜底回退 (Fallback Defaults)
        # 场景: 数据库连接失败、配置未同步、或未传递 db session
        # 作用: 保证系统核心功能在配置缺失时仍能降级运行 (Graceful Degradation)
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
    async def _call_siliconflow(prompt: str, model: str, api_key: str, db: AsyncSession = None) -> str:
        """
        调用硅基流动 (SiliconFlow) API 通用方法
        
        Args:
            prompt (str): 发送给 LLM 的完整提示词
            model (str): 模型 Key (e.g., "deepseek-r1", "qwen-3-vl-thinking")
            api_key (str): SiliconFlow/DeepSeek API Key
            db (AsyncSession): 数据库会话，用于动态查询模型配置 ID
            
        Returns:
            str: LLM 返回的文本内容 (Content String)
        """
        url = "https://api.siliconflow.cn/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 1. 获取动态模型 ID (Resolve Model ID)
        # 从数据库或缓存中查找 Key 对应的真实 Model ID (e.g. "Pro/deepseek-ai/DeepSeek-R1")
        config = await AIService.get_model_config(model, db)
        model_id = config.model_id
        
        logger.info(f"Calling SiliconFlow with Model ID: {model_id} (Key: {model})")

        # 2. 构建请求载荷 (Construct Payload)
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            # JSON Mode: 如果非 Google 模型，则尝试强制 JSON 输出以保证解析稳定性
            "response_format": {"type": "json_object"} if "gemini" not in model else None, 
            "stream": False,
            "temperature": 0.3  # 低温度以保证分析结果的理性和一致性
        }
        
        try:
            # 3. 发送异步 HTTP 请求 (Async HTTP Request)
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                # 4. 错误处理 (Error Handling)
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"SiliconFlow API Error ({response.status_code}): {error_detail}")
                    return f"**Error**: SiliconFlow 调用失败 (HTTP {response.status_code})。详情: {error_detail}"
                
                result = response.json()
                # 提取核心内容
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            import traceback
            logger.error(f"SiliconFlow Exception: {str(e)}\n{traceback.format_exc()}")
            return f"**Error**: SiliconFlow 网络异常。{str(e)}"

    @staticmethod
    async def generate_analysis(ticker: str, market_data: dict, portfolio_data: dict, news_data: list = None, fundamental_data: dict = None, model: str = "gemini-1.5-flash", api_key_gemini: str = None, api_key_siliconflow: str = None, db: AsyncSession = None) -> str:
        """
        生成单支股票的深度投资分析报告 (Generate Single Stock Analysis)
        
        Args:
            ticker (str): 股票代码 (e.g., "AAPL")
            market_data (dict): 实时行情数据 (Price, RSI, MACD, Bollinger Bands, KDJ, etc.)
            portfolio_data (dict): 用户持仓信息 (Cost, Quantity, Unrealized P/L)
            news_data (list): 最近新闻摘要列表，用于 RAG 上下文注入
            fundamental_data (dict): 基础面数据 (PE, Market Cap, Sector, etc.)
            model (str): 指定使用的模型 Key
            db (AsyncSession): 数据库会话
            
        Returns:
            str: JSON 格式的分析报告 (raw string)，包含 sentiment_score, action_advice, technical_analysis 等字段
            
        流程 (Workflow):
        1. 构建包含所有上下文 (技术/基本/持仓/新闻) 的超长 System Prompt
        2. 动态加载模型配置 (Gemini vs SiliconFlow)
        3. 调用对应 API 并获取 JSON 响应
        """
        # 构建 Prompt (Construct Prompt)
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
            
### 1. 建议操作与交易综述 (Suggested Action & Executive Summary)
- **建议操作**: **[即时行动建议]**
- **行情综述**: 当前股价 **$价格** 处于 **[阶段定义]**。整体研判为 **[策略定调]**。

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
        # 获取模型配置，判断 Provider
        model_config = await AIService.get_model_config(model, db)
        provider = model_config.provider
        
        if provider == "gemini":
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
            return await AIService._call_siliconflow(prompt, model, key, db)
    @staticmethod
    async def generate_portfolio_analysis(portfolio_items: list, market_news: str = None, model: str = "gemini-1.5-flash", api_key_gemini: str = None, api_key_siliconflow: str = None, db: AsyncSession = None) -> str:
        """
        生成全量持仓健康诊断报告 (Generate Portfolio Health Check)
        
        Args:
            portfolio_items (list): 持仓列表 (包含 ticker, market_value, pl_percent, sector)
            market_news (str): 聚合的市场宏观新闻 & 头部持仓个性化新闻 (RAG Context)
            model (str): 指定模型 Key
            db (AsyncSession): 数据库会话
            
        Returns:
            str: JSON 格式的深度诊断报告 (raw string)，包含 health_score, strategic_advice, detailed_report 等字段
            
        流程 (Workflow):
        1. 聚合持仓数据，计算总市值与权重
        2. 注入外部 RAG 新闻上下文
        3. 构建 "全景扫描" System Prompt
        4. 调用 LLM 生成结构化诊断建议
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
        
        **2. 实时市场与新闻背景 (Real-time Market Context)**:
        {market_news if market_news else "暂无外部实时新闻，请基于已有持仓数据进行存量分析。"}
        
        **3. 分析指令 (Strict Directives)**:
        1. **深度风险透视**: 不仅要指出行业分布，还要识别“隐性关联”（例如：如果同时持有半导体和科技服务）。指出哪个标的对组合的整体风险贡献最大。
        2. **盈亏属性分析**: 分别针对“浮盈巨大”和“严重套牢”的标的给出具体的处理建议（止盈、补仓或止损）。
        3. **调仓战略建议**: 给出未来一周的动作指南（例如：保持当前防御性配置、增加避险资产比例、或激进捕捉反弹）。
        4. **禁止空话**: 严禁使用“视市场情况而定”等通用废话。必须根据数据给出倾向于具体行动的判断。
        
        **返回格式要求**:
        - 必须返回纯 JSON 对象，不能包含任何 ```json 或 Markdown 前缀/后缀。
        - 结果必须是合法的 JSON 格式。
        - **详尽报告排版准则 (Layout Rules)**:
            *   使用 `###` 作为一级标题，`####` 作为二级标题。
            *   **必须使用 Markdown 表格**来对比核心数据（如：标的 | 权重 | 盈亏 | 建议动作）。
            *   对关键行情数据和操作点位使用 **加粗**。
            *   保持段落简洁，每个逻辑块之间留有空行。
        
        JSON 结构模版:
        {{
            "health_score": 0-100 (整数),
            "risk_level": "低/中/高",
            "summary": "一句话核心结论 (15字以内)",
            "diversification_analysis": "关于相关性与分散度的硬核分析",
            "strategic_advice": "具体的战术动作指南 (加仓/减仓/调仓)",
            "top_risks": ["具体风险点1", "具体风险点2"],
            "top_opportunities": ["具体机会点1", "具体机会点2"],
            "detailed_report": "深度 Markdown 诊断报告。结构建议：
            ### 1. 组合现状透视 (Portfolio Status)
            [简述]
            
            #### 资产配置矩阵
            | 标的 | 当前价格 | 仓位占比 | 盈亏状态 | 建议动作 |
            | :--- | :--- | :--- | :--- | :--- |
            | [Ticker] | $xx | xx% | +xx% | **[动作]** |
            
            ### 2. 深度风险与驱动因素 (Risk & Dynamics)
            [结合实时新闻背景的深度解读]
            
            ### 3. 下周战术指南 (Weekly Tactical Plan)
            * **核心防御**: [建议]
            * **进攻机会**: [建议]
            "
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
            return await AIService._call_siliconflow(prompt, model, key, db)
