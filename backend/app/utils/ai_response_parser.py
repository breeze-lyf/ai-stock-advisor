"""
AI 响应 JSON 解析工具 (AI Response JSON Parser)

统一的 AI 响应 JSON 提取与清洗逻辑。
消除 analysis.py 中 3 处重复的解析代码，一处修改全局生效。
"""
import json
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# 默认的降级字典模板，当 AI 返回错误或 JSON 解析失败时使用
_ERROR_FALLBACK = {
    "sentiment_score": 50,
    "summary_status": "调用失败",
    "risk_level": "未知",
    "technical_analysis": "",
    "fundamental_news": "",
    "action_advice": "",
}

_PARSE_FAIL_FALLBACK = {
    "sentiment_score": 50,
    "summary_status": "解析失败",
    "risk_level": "中",
}


def parse_ai_json(raw_response: str, context: str = "unknown") -> dict:
    """
    统一的 AI 响应 JSON 提取器。

    处理流程：
    1. 检测 **Error** 前缀 → 返回降级字典（AI 服务层已经返回了明确的错误信息）
    2. 正则提取第一个 { 到最后一个 } 之间的内容
    3. 清洗控制字符、markdown 包装（```json ... ```）
    4. json.loads 解析
    5. 全部失败 → 将原始文本塞入 detailed_report / technical_analysis 字段，防止前端全空

    参数:
        raw_response: AI 返回的原始字符串
        context: 调用场景标识（如 "stock_analysis" / "portfolio_analysis"），用于日志区分

    返回:
        解析后的字典。保证不会抛异常，始终返回一个可用的 dict。
    """
    if not raw_response:
        logger.warning(f"[{context}] AI 响应为空")
        return {**_ERROR_FALLBACK, "technical_analysis": "AI 未返回任何内容。"}

    raw_response = raw_response.strip()

    # ——— 阶段 1：检测 AI 服务层显式错误 ———
    if raw_response.startswith("**Error**"):
        logger.error(f"[{context}] AI 服务返回错误: {raw_response}")
        return {
            **_ERROR_FALLBACK,
            "technical_analysis": f"AI 服务调用异常: {raw_response}",
            "action_advice": "由于 AI 接口调用失败，暂时无法生成详细诊断建议。请检查 API 配置或稍后重试。",
        }

    # ——— 阶段 2：尝试提取并解析 JSON ———
    try:
        # 策略 A：正则提取最外层 {} 块（处理前后可能有的杂质文本）
        json_match = re.search(r'(\{.*\})', raw_response, re.DOTALL)
        if json_match:
            clean_json = json_match.group(1)
            # 移除可能混入的控制字符（如零宽字符、换行符等），但保留正常的空白
            clean_json = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', clean_json)
            return json.loads(clean_json)

        # 策略 B：兜底——去掉 markdown 代码块包装后直接解析
        clean_text = raw_response
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        return json.loads(clean_text.strip())

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"[{context}] JSON 解析失败: {e}. 原始响应前 200 字符: {raw_response[:200]}...")

    # ——— 阶段 3：全军覆没，返回降级字典 ———
    # 将原始文本塞入可展示的字段，确保用户至少能看到 AI 的原始回答
    fallback = {**_PARSE_FAIL_FALLBACK}
    if len(raw_response) > 50:
        fallback["technical_analysis"] = raw_response
        fallback["action_advice"] = "AI 响应格式解析失败，请查看技术分析详情。"
        fallback["detailed_report"] = raw_response
    else:
        fallback["action_advice"] = raw_response
        fallback["detailed_report"] = raw_response

    return fallback


def parse_portfolio_ai_json(raw_response: str) -> dict:
    """
    组合分析专用的 JSON 解析入口。
    
    与 parse_ai_json 共享核心解析逻辑，但在降级时使用组合分析特有的字段结构。
    """
    parsed = parse_ai_json(raw_response, context="portfolio_analysis")

    # 如果核心解析成功（包含 health_score），直接返回
    if "health_score" in parsed:
        return parsed

    # 否则，适配组合分析的响应结构
    return {
        "health_score": parsed.get("sentiment_score", 50),
        "risk_level": parsed.get("risk_level", "中"),
        "summary": parsed.get("summary_status", "AI 诊断已完成 (点击查看详情)"),
        "diversification_analysis": "解析失败，详细请见报告。",
        "strategic_advice": "请直接阅读下方深度诊断报告。",
        "top_risks": ["无法自动提取风险点"],
        "top_opportunities": ["无法自动提取机会点"],
        "detailed_report": parsed.get("detailed_report", raw_response),
    }
