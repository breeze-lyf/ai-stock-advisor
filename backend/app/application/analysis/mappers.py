from __future__ import annotations
from typing import Any

from app.application.analysis.helpers import (
    extract_entry_prices_fallback,
    extract_entry_zone_fallback,
    to_float,
    to_str,
)
from app.models.analysis import AnalysisReport
from app.utils.ai_response_parser import parse_ai_json


def _list_of_dicts_or_none(value: Any) -> list[dict[str, Any]] | None:
    if not isinstance(value, list):
        return None

    cleaned = [item for item in value if isinstance(item, dict)]
    return cleaned or None


def serialize_analysis_report(
    report: AnalysisReport,
    rr_ratio: str | None = None,
    history_price: float | None = None,
) -> dict[str, Any]:
    raw_payload = parse_ai_json(report.ai_response_markdown or "", context=f"report_{report.ticker}")

    return {
        "ticker": report.ticker,
        "analysis": report.ai_response_markdown,
        "decision_mode": to_str(raw_payload.get("decision_mode")),
        "dominant_driver": to_str(raw_payload.get("dominant_driver")),
        "trade_setup_status": to_str(raw_payload.get("trade_setup_status")),
        "sentiment_score": to_float(report.sentiment_score),
        "summary_status": report.summary_status,
        "risk_level": report.risk_level,
        "trigger_condition": to_str(raw_payload.get("trigger_condition")),
        "invalidation_condition": to_str(raw_payload.get("invalidation_condition")),
        "next_review_point": to_str(raw_payload.get("next_review_point")),
        "technical_analysis": report.technical_analysis,
        "fundamental_news": report.fundamental_news,
        "news_summary": to_str(raw_payload.get("news_summary")) or report.fundamental_news,
        "fundamental_analysis": to_str(raw_payload.get("fundamental_analysis")),
        "macro_risk_note": to_str(raw_payload.get("macro_risk_note")),
        "add_on_trigger": to_str(raw_payload.get("add_on_trigger")),
        "action_advice": report.action_advice,
        "investment_horizon": report.investment_horizon,
        "confidence_level": report.confidence_level,
        "immediate_action": report.immediate_action,
        "target_price": report.target_price,
        "target_price_1": to_float(raw_payload.get("target_price_1")),
        "target_price_2": to_float(raw_payload.get("target_price_2")),
        "stop_loss_price": report.stop_loss_price,
        "max_position_pct": to_float(raw_payload.get("max_position_pct")),
        "entry_zone": report.entry_zone or extract_entry_zone_fallback(report.action_advice),
        "entry_price_low": report.entry_price_low
        if report.entry_price_low is not None
        else extract_entry_prices_fallback(report.action_advice)[0],
        "entry_price_high": report.entry_price_high
        if report.entry_price_high is not None
        else extract_entry_prices_fallback(report.action_advice)[1],
        "rr_ratio": rr_ratio or report.rr_ratio,
        "bull_case": to_str(raw_payload.get("bull_case")),
        "base_case": to_str(raw_payload.get("base_case")),
        "bear_case": to_str(raw_payload.get("bear_case")),
        "scenario_tags": _list_of_dicts_or_none(report.scenario_tags),
        "thought_process": _list_of_dicts_or_none(report.thought_process),
        "is_cached": True,
        "model_used": report.model_used,
        "report_scope": getattr(report, "report_scope", None),
        "created_at": report.created_at,
        "history_price": history_price,
    }
