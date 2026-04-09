"""
AI 提示词模板中心 (AI Prompt Templates Center)

将巨型 Prompt 从服务代码中解耦，便于策略迭代与版本管理。
"""
from datetime import datetime

# 合规性免责声明
COMPLIANCE_DISCLAIMER = (
    "【风险提示】本分析由 AI 自动生成，仅供参考，不构成任何投资建议。股市有风险，投资需谨慎。\n"
    "【数据说明】本分析基于历史公开数据及量化模型，不保证未来收益及数据的绝对准确性。\n\n"
)

# ---------------------------------------------------------------------------
# StockCapsule 预计算摘要提示词 (轻量级，无需深度 thinking 模式)
# ---------------------------------------------------------------------------

NEWS_CAPSULE_PROMPT_TEMPLATE = """
你是一位专业的股市新闻分析师。请对以下关于 [{ticker}] 的最新新闻和宏观资讯进行简洁的摘要分析。

**个股新闻 (Stock-specific news, most recent first):**
{stock_news_context}

**宏观快讯 (Global macro headlines):**
{macro_news_context}

**输出要求:**
- 使用中文，简洁专业。
- 提取 3-5 个最关键的消息面观察点。
- 指出消息面对该股的整体情绪倾向（利好/利空/中性）。
- 用 Markdown 格式输出，包含：**情绪总结**、**关键事件摘要**、**潜在影响分析**。
- 严禁编造细节，仅基于所提供的新闻内容。
- 如果新闻稀少或不相关，直接说明"近期无重大消息面催化剂"。
- 输出长度控制在 400 字以内。
"""

FUNDAMENTAL_CAPSULE_PROMPT_TEMPLATE = """
你是一位专业的基本面分析师。请对以下 [{ticker}] 的基本面数据进行简洁的快速诊断。

**基本面数据:**
- 行业/板块: {sector} / {industry}
- 市值: {market_cap}
- PE (TTM): {pe_ratio} | Forward PE: {forward_pe}
- Beta: {beta}
- 52周区间: [{fifty_two_week_low}, {fifty_two_week_high}]
- 分析师共识: {analyst_summary}
- 现价: {current_price}

**输出要求:**
- 使用中文，简洁专业。
- 快速评估估值水位（是否偏贵/合理/低估）。
- 点评行业地位与市场敏感度（Beta 含义）。
- 用 Markdown 格式输出，包含：**估值快照**、**行业定位**、**分析师观点**。
- 输出长度控制在 300 字以内。
"""

STOCK_ANALYSIS_PROMPT_TEMPLATE = """
{compliance_prefix}你是一位资深全球多市场投资顾问和量化策略专家，精通美股（纳斯达克/纽交所）、A股（汪深两市）及港股的不同交易结构与市场特性。请基于以下多维数据为代码 [{ticker}] 提供严谨的诊断。
注意：这是**标的级公共分析**，不面向某个具体用户持仓；禁止根据个体仓位、成本价、盈亏情况输出个性化持仓建议。

**1. 基础面概览 (Fundamental Context)**:
- [REF_F1] 行业/板块: {sector} / {industry}
- [REF_F2] 市值: {market_cap}
- [REF_F3] PE (TTM): {pe_ratio} | Forward PE: {forward_pe}
- [REF_F4] 52周波动范围: [{fifty_two_week_low}, {fifty_two_week_high}]
- [REF_F5] Beta: {beta}

**2. 分析模式 (Analysis Mode)**:
- [REF_P0] 当前分析模式: {decision_mode}

**3. 实时技术面数据 (Technical Data)**:
- [REF_T1] 当前价格: ${current_price}
- [REF_T2] 今日涨跌: {change_percent}%
- [REF_T3] RSI (14): {rsi_14}
- [REF_T3.5] 量比 (Vol vs 20MA): {volume_ratio} (参考: >1.5 = 放量有效，0.5-1.5 = 正常，<0.5 = 缩量萌退)
- [REF_T4] KDJ (K): {k_line} / (D): {d_line} / (J): {j_line}
- [REF_T5] MACD: {macd_val} (柱状图: {macd_hist}, 斜率: {macd_hist_slope})
- [REF_T6] 布林带 (BB): 上轨: {bb_upper} | 均线: {bb_middle} | 下轨: {bb_lower}
- [REF_T7] MA 均线: [20: {ma_20}, 50: {ma_50}, 200: {ma_200}]
- [REF_T8] 趋势强度 (ADX): {adx_14}（参考: >25=趋势确立可跟趋，20-25=趋势形成中，<20=区间震荡慎跟）| ATR: {atr_14}
- [REF_T9] 枢轴参考 (Pivots): 阻力位 R1: {resistance_1} / R2: {resistance_2} | 支撑位 S1: {support_1} / S2: {support_2}

**4. 实时个股消息面与资金流 (News & Capital Flow)**:
- [REF_N1] 消息面: {news_context}
- [REF_N2] 筹码动向: 今日主力净流入 **{net_inflow}** 元。
- [REF_N3] 估值水位: 当前 PE 百分位为 **{pe_percentile}%**，PB 百分位为 **{pb_percentile}%**。

**4.5. 预计算消息面摘要 (Pre-computed News Capsule)** *(仅供参考，以上 REF_N1 原始新闻为准)*:
{pre_computed_news}

**4.6. 预计算基本面摘要 (Pre-computed Fundamental Capsule)** *(仅供参考，以上 REF_F 原始数据为准)*:
{pre_computed_fundamental}

**5. 全球宏观雷达与热点 (Global Macro Radar & Hotspots)**:
[CONTEXT]: 以下是当前对全球市场影响最大的热点。
- [REF_M1] 宏观偏见: {macro_context}

**6. 关键日历与宏观指标 (Key Calendar & Macro Gauge)**:
- [REF_C1] 下次 FOMC 利率决议距今: {fomc_days_away} 天 (日期: {next_fomc_date})
- [REF_C2] 财报日期: {earnings_date}
- [REF_C3] 当前 VIX 恐慌指数: {vix_level}（参考: <15=低波动, 15-25=正常, 25-35=高波动, >35=极度恐慌）
- [REF_C4] 分析师共识: {analyst_summary}

**7. 历史分析上下文 (Historical Context)**:
{previous_analysis_context}

**返回格式要求**:
- 使用简洁、专业的中文。
- 你不是在写研报，而是在生成一份**可执行交易计划**。
- 必须先判断：当前处于什么交易结构（回踩等待/突破观察/区间震荡/趋势延续）；当前主驱动是什么；当前交易计划是否已触发。
- **核心逻辑优先**: `core_logic_summary` 必须是 3 句以内的极简总结，用于快速决策。
- **严谨精度**: 所有数值保留 2 位小数点。
- 必须返回严格的 JSON 格式。
- `action_advice` 应输出为**结构化 Markdown**，侧重于深层的逻辑分析和证据支撑。
- `action_advice` 必须包含以下 3 个章节：
  1. `1. 研判综述` (简明扼要)
  2. `2. 结构化操作计划` (关键点位)
  3. `3. 多维逻辑支撑` (深度证据)
- **表格渲染规范**: 在“多维逻辑支撑”中，必须使用**标准 Markdown 表格语法**（使用单个 `|` 作为列分隔符），**绝对禁止**使用双竖线 `||`。
- **表格示例**:
  | 维度 | 核心数据 | 研判意义 |
  | :--- | :--- | :--- |
  | 技术面 | RSI=75 | 进入超买区，需警惕回调 |
  | 资金面 | 净流入 2.5 亿 | 主力吸筹迹象明显 |
- 这是标的级公共分析，禁止出现“继续持有”“你当前仓位”“减仓到多少”之类依赖个人持仓的表述。
- 应聚焦于标的本身是否值得观察、等待、开仓、加仓触发和计划失效条件。
- 每条关键结论至少绑定 1 个输入证据；若关键数据缺失（N/A），必须明确写“证据不足”，并下调置信度。
- 严禁在 `news_summary` 中编造具体事件名称、会议、监管动作或日期；引用事件时必须能在 `news_context` 找到依据。
- `fundamental_analysis` 只允许基于基础面与估值数据，禁止引用新闻与宏观。
- `macro_risk_note` 只允许基于 `macro_context`，并说明影响传导链，不得伪装成个股新闻结论。
- `entry_price_low` / `entry_price_high` 是盈亏比计算核心依据，**必须给出具体价格**，且严格满足：`stop_loss_price` < `entry_price_low` ≤ `entry_price_high` < `target_price`。

JSON 结果结构:
{{
    "decision_mode": "标的通用分析",
    "dominant_driver": "技术面/消息面/基本面/估值修复/宏观扰动/混合",
    "trade_setup_status": "已触发/接近触发/未触发/失效",
    "sentiment_score": 0-100, 
    "summary_status": "4-6字定调",
    "immediate_action": "决策建议",
    "core_logic_summary": "3句以内的核心逻辑精简总结",
    "trigger_condition": "计划生效条件",
    "invalidation_condition": "计划失效条件",
    "next_review_point": "下一次复核价格或时间点",
    "catalyst": "本次交易的核心催化剂（技术突破/消息事件/估值修复），简洁单句",
    "entry_price_low": Float,
    "entry_price_high": Float,
    "add_on_trigger": "加仓触发条件",
    "target_price": Float,
    "target_price_1": Float,
    "target_price_2": Float,
    "stop_loss_price": Float,
    "max_position_pct": Float,
    "risk_level": "低/中/高",
    "investment_horizon": "日内 | 0-5天 | 1-2周 | 1-3月 | 3月以上",
    "confidence_level": 0-100,
    "confidence_breakdown": {{
        "technical": 0-100,
        "fundamental": 0-100,
        "macro": 0-100,
        "sentiment": 0-100
    }},
    "key_assumptions": [
        {{"assumption": "核心假设描述（如：季度业绩超预期）", "breakpoint": "该假设失效的触发条件（如：EPS<预期10%以上）"}}
    ],
    "thought_process": [
        {{"step": "观察", "content": "..."}},
        {{"step": "推导", "content": "..."}},
        {{"step": "结论", "content": "..."}}
    ],
    "scenario_tags": [
        {{"category": "技术形态 | 市场结构 | 基本面驱动 | 宏观风险 | 情绪极値 | 量价关系", "value": "简短标签，如: 双底突破/强支撑测试/RSI超卖/主力流入"}}
    ],
    "catalysts": [
        {{"date": "YYYY-MM-DD 或 '未知'", "event": "催化剂事件名称", "type": "earnings | fomc | product | macro | technical", "impact": "bullish | bearish | neutral", "description": "一句话影响说明"}}
    ],
    "technical_analysis": "核心技术位解读。结论先行。",
    "news_summary": "基于消息面的综述。",
    "fundamental_analysis": "基本面指标解读。",
    "macro_risk_note": "宏观/政策风险说明。",
    "bull_case": "乐观情景与触发条件",
    "base_case": "基准情景与计划执行路径",
    "bear_case": "悲观情景与风险控制条件",
    "action_advice": "Markdown 详细操作建议。建议使用表格展示支撑数据。"
}}
"""

PORTFOLIO_ANALYSIS_PROMPT_TEMPLATE = """
你是一位资深私人财富管理顾问和首席投资策略师。请对用户的**整个投资组合**进行全面的“全景扫描”与健康诊断。

**1. 持仓明细 (Portfolio Breakdown)**:
{holdings_context}

**2. 宏观环境与外部背景 (Global Macro & Market Context)**:
{macro_context}

**3. 补充市场新闻 (Additional News)**:
{market_news}

**4. 分析指令 (Professional Analyst Directives)**:
1. **多维诊断矩阵**: 必须独立分析 **技术面、基本面（估值水位）、筹码面（资金动向）**。
2. **宏观一致性逻辑**: 建立“宏观背景 -> 行业趋势 -> 具体标的”的逻辑传导链。
3. **风险系数监测**: 分析组合的 Beta 暴露，指出是否存在行业过度拥挤。
4. **止盈/止损实战建议**: 对每个关键持仓标的，基于数据定性 [继续持有/分批获利/逻辑证伪止损]。

**返回格式要求**:
- 必须返回纯 JSON 对象。
- 详尽报告排版请包含：【专业诊断表】、【核心宏观传导逻辑】、【调仓战略指南】。

JSON 结构模版:
{{
    "health_score": 0-100,
    "risk_level": "低/中/高",
    "summary": "核心结论（一句话）",
    "strategic_advice": "战术动作指南",
    "top_risks": ["风险点1", "风险点2", "风险点3"],
    "top_opportunities": ["机会点1", "机会点2", "机会点3"],
    "detailed_report": "深度 Markdown 诊断报告"
}}
"""

def build_stock_analysis_prompt(ticker: str, market_data: dict, fundamental_data: dict, news_data: list, macro_context: str, previous_analysis: dict = None, fomc_days_away: int = None, next_fomc_date: str = None, earnings_date: str = None, vix_level: float = None, analyst_summary: str = None, pre_computed_news: str = None, pre_computed_fundamental: str = None) -> str:
    news_context = "\n".join([f"- {n['title']} ({n['publisher']})" for n in news_data]) if news_data else "暂无重大个股新闻。"
    
    prev_context = "该股票首次进行 AI 分析。"
    if previous_analysis:
        prev_context = f"""- [REF_H1] 上次研判结论: {previous_analysis.get('summary_status', '无')} (评分: {previous_analysis.get('sentiment_score', '无')})
- [REF_H2] 上次策略建议: {previous_analysis.get('immediate_action', '无')}"""

    # 处理行情数据
    current_price = market_data.get('current_price', 0)
    change_percent = market_data.get('change_percent', 0)
    decision_mode = "标的通用分析"
    
    return STOCK_ANALYSIS_PROMPT_TEMPLATE.format(
        compliance_prefix=COMPLIANCE_DISCLAIMER,
        ticker=ticker,
        sector=fundamental_data.get('sector', '未知'),
        industry=fundamental_data.get('industry', '未知'),
        market_cap=fundamental_data.get('market_cap', 'N/A'),
        pe_ratio=fundamental_data.get('pe_ratio', 'N/A'),
        forward_pe=fundamental_data.get('forward_pe', 'N/A'),
        fifty_two_week_low=fundamental_data.get('fifty_two_week_low', 'N/A'),
        fifty_two_week_high=fundamental_data.get('fifty_two_week_high', 'N/A'),
        beta=fundamental_data.get('beta', '1.0'),
        decision_mode=decision_mode,
        current_price=current_price,
        change_percent=change_percent,
        rsi_14=market_data.get('rsi_14', 'N/A'),
        volume_ratio=market_data.get('volume_ratio', 'N/A'),
        k_line=market_data.get('k_line', 'N/A'),
        d_line=market_data.get('d_line', 'N/A'),
        j_line=market_data.get('j_line', 'N/A'),
        macd_val=market_data.get('macd_val', 'N/A'),
        macd_hist=market_data.get('macd_hist', 'N/A'),
        macd_hist_slope=market_data.get('macd_hist_slope', 'N/A'),
        bb_upper=market_data.get('bb_upper', 'N/A'),
        bb_middle=market_data.get('bb_middle', 'N/A'),
        bb_lower=market_data.get('bb_lower', 'N/A'),
        ma_20=market_data.get('ma_20', 'N/A'),
        ma_50=market_data.get('ma_50', 'N/A'),
        ma_200=market_data.get('ma_200', 'N/A'),
        adx_14=market_data.get('adx_14', 'N/A'),
        atr_14=market_data.get('atr_14', 'N/A'),
        resistance_1=market_data.get('resistance_1', 'N/A'),
        resistance_2=market_data.get('resistance_2', 'N/A'),
        support_1=market_data.get('support_1', 'N/A'),
        support_2=market_data.get('support_2', 'N/A'),
        news_context=news_context,
        net_inflow=market_data.get('net_inflow', 'N/A'),
        pe_percentile=market_data.get('pe_percentile', 'N/A'),
        pb_percentile=market_data.get('pb_percentile', 'N/A'),
        macro_context=macro_context or "暂无重大宏观指引。",
        fomc_days_away=fomc_days_away if fomc_days_away is not None else "N/A",
        next_fomc_date=next_fomc_date or "N/A",
        earnings_date=earnings_date or "N/A",
        vix_level=f"{vix_level:.2f}" if vix_level is not None else "N/A",
        analyst_summary=analyst_summary or "N/A",
        previous_analysis_context=prev_context,
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        pre_computed_news=pre_computed_news or "暂无预计算消息面摘要。",
        pre_computed_fundamental=pre_computed_fundamental or "暂无预计算基本面摘要。",
    )

def build_portfolio_analysis_prompt(holdings_context: str, macro_context: str, market_news: str) -> str:
    return PORTFOLIO_ANALYSIS_PROMPT_TEMPLATE.format(
        holdings_context=holdings_context,
        macro_context=macro_context or "暂无重大宏观指引。",
        market_news=market_news or "暂无重大市场新闻。"
    )
