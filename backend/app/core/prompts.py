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

STOCK_ANALYSIS_PROMPT_TEMPLATE = """
{compliance_prefix}你是一位资深美股投资顾问和量化策略专家。请基于以下多维数据为代码 [{ticker}] 提供严谨的诊断。

**1. 基础面概览 (Fundamental Context)**:
- [REF_F1] 行业/板块: {sector} / {industry}
- [REF_F2] 市值: {market_cap}
- [REF_F3] PE (TTM): {pe_ratio} | Forward PE: {forward_pe}
- [REF_F4] 52周波动范围: [{fifty_two_week_low}, {fifty_two_week_high}]
- [REF_F5] Beta: {beta}

**2. 用户持仓背景 (Portfolio Context)**:
- [REF_P1] 当前成本价: ${avg_cost}
- [REF_P2] 持仓数量: {quantity}
- [REF_P3] 未实现盈亏: ${unrealized_pl} ({pl_percent}%)

**3. 实时技术面数据 (Technical Data)**:
- [REF_T1] 当前价格: ${current_price}
- [REF_T2] 今日涨跌: {change_percent}%
- [REF_T3] RSI (14): {rsi_14}
- [REF_T4] KDJ (K): {k_line} / (D): {d_line} / (J): {j_line}
- [REF_T5] MACD: {macd_val} (柱状图: {macd_hist}, 斜率: {macd_hist_slope})
- [REF_T6] 布林带 (BB): 上轨: {bb_upper} | 均线: {bb_middle} | 下轨: {bb_lower}
- [REF_T7] MA 均线: [20: {ma_20}, 50: {ma_50}, 200: {ma_200}]
- [REF_T8] 趋势强度 (ADX): {adx_14} | ATR: {atr_14}
- [REF_T9] 枢轴参考 (Pivots): 阻力位 R1: {resistance_1} / R2: {resistance_2} | 支撑位 S1: {support_1} / S2: {support_2}

**4. 实时个股消息面与资金流 (News & Capital Flow)**:
- [REF_N1] 消息面: {news_context}
- [REF_N2] 筹码动向: 今日主力净流入 **{net_inflow}** 元。
- [REF_N3] 估值水位: 当前 PE 百分位为 **{pe_percentile}%**，PB 百分位为 **{pb_percentile}%**。

**5. 全球宏观雷达与热点 (Global Macro Radar & Hotspots)**:
[CONTEXT]: 以下是当前对全球市场影响最大的热点。
- [REF_M1] 宏观偏见: {macro_context}

**6. 历史分析上下文 (Historical Context)**:
{previous_analysis_context}

**任务 (Core Task)**:
当前时间: {current_time}
请执行“逻辑严密”的投资诊断。

**重要准则 (Strict Rules)**:
- **数据驱动 [CRITICAL]**: 每个关键分析点必须基于提供的数据源。
- **持仓逻辑**: 如果用户当前持仓为 0，建议应侧重于建仓点位。
- **仓位管理**: 所有的仓位建议必须基于**总资金的百分比**。

**返回格式要求**:
- 使用简洁、专业的中文。
- **严谨精度**: 所有数值保留 2 位小数点。
- 必须返回严格的 JSON 格式。

JSON 结果结构:
{{
    "sentiment_score": 0-100, 
    "summary_status": "4-6字定调",
    "immediate_action": "决策建议",
    "rr_ratio": "盈亏比评价",
    "entry_price_low": Float,
    "entry_price_high": Float,
    "target_price": Float,
    "stop_loss_price": Float,
    "risk_level": "低/中/高",
    "investment_horizon": "建议持仓期限",
    "confidence_level": 0-100,
    "thought_process": [
        {{"step": "观察", "content": "基于数据的发现..."}},
        {{"step": "推导", "content": "逻辑关联分析..."}},
        {{"step": "风险评估", "content": "潜在的证伪条件..."}},
        {{"step": "结论", "content": "最终行动定调..."}}
    ],
    "scenario_tags": [
        {{"category": "技术形态", "value": "空中加油"}},
        {{"category": "资金面", "value": "机构持续净流入"}}
    ],
    "technical_analysis": "核心技术位解读。使用 Markdown，结论先行。",
    "fundamental_news": "基础面/消息面深度解读",
    "action_advice": "Markdown 格式的操作建议。"
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
    "summary": "核心结论",
    "strategic_advice": "战术动作指南",
    "detailed_report": "深度 Markdown 诊断报告"
}}
"""

def build_stock_analysis_prompt(ticker: str, market_data: dict, portfolio_data: dict, fundamental_data: dict, news_data: list, macro_context: str, previous_analysis: dict = None) -> str:
    news_context = "\n".join([f"- {n['title']} ({n['publisher']})" for n in news_data]) if news_data else "暂无重大个股新闻。"
    
    prev_context = "该股票首次进行 AI 分析。"
    if previous_analysis:
        prev_context = f"""- [REF_H1] 上次研判结论: {previous_analysis.get('summary_status', '无')} (评分: {previous_analysis.get('sentiment_score', '无')})
- [REF_H2] 上次策略建议: {previous_analysis.get('immediate_action', '无')}"""

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
        beta=fundamental_data.get('beta', 'N/A'),
        avg_cost=portfolio_data.get('avg_cost', 0),
        quantity=portfolio_data.get('quantity', 0),
        unrealized_pl=portfolio_data.get('unrealized_pl', 0),
        pl_percent=portfolio_data.get('pl_percent', 0),
        current_price=market_data.get('current_price', 'N/A'),
        change_percent=market_data.get('change_percent', 0),
        rsi_14=market_data.get('rsi_14', 'N/A'),
        k_line=market_data.get('k_line', 'N/A'),
        d_line=market_data.get('d_line', 'N/A'),
        j_line=market_data.get('j_line', 'N/A'),
        macd_val=market_data.get('macd_val', 'N/A'),
        macd_hist=market_data.get('macd_hist', 'N/A'),
        macd_hist_slope=market_data.get('macd_hist_slope', 0),
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
        net_inflow=fundamental_data.get('net_inflow', 'N/A'),
        pe_percentile=fundamental_data.get('pe_percentile', 'N/A'),
        pb_percentile=fundamental_data.get('pb_percentile', 'N/A'),
        macro_context=macro_context or "暂无显著全球宏观波动。",
        previous_analysis_context=prev_context,
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

def build_portfolio_analysis_prompt(portfolio_items: list, market_news: str, macro_context: str) -> str:
    holdings_context = ""
    total_market_value = sum(item.get('market_value', 0) for item in portfolio_items)
    for item in portfolio_items:
        weight = (item.get('market_value', 0) / total_market_value * 100) if total_market_value > 0 else 0
        holdings_context += f"- [{item['ticker']}] {item['name']}: 仓位 {weight:.2f}%, 盈亏 {item['pl_percent']:.2f}%, 行业: {item.get('sector', '未知')}\n"
    
    return PORTFOLIO_ANALYSIS_PROMPT_TEMPLATE.format(
        holdings_context=holdings_context,
        macro_context=macro_context or "当前无显著宏观热点波动。",
        market_news=market_news or "暂无外部实时新闻。"
    )
