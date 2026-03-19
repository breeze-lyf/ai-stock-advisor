from __future__ import annotations
from typing import Any

from app.application.analysis.helpers import (
    extract_entry_prices_fallback,
    extract_entry_zone_fallback,
)
from app.models.analysis import AnalysisReport
from app.utils.ai_response_parser import parse_ai_json


def serialize_analysis_report(
    report: AnalysisReport,
    rr_ratio: str | None = None,
    history_price: float | None = None,
) -> dict[str, Any]:
    raw_payload = parse_ai_json(report.ai_response_markdown or "", context=f"report_{report.ticker}")

    return {
        "ticker": report.ticker,
        "analysis": report.ai_response_markdown,
        "decision_mode": raw_payload.get("decision_mode"),
        "dominant_driver": raw_payload.get("dominant_driver"),
        "trade_setup_status": raw_payload.get("trade_setup_status"),
        "sentiment_score": float(report.sentiment_score) if report.sentiment_score else None,
        "summary_status": report.summary_status,
        "risk_level": report.risk_level,
        "trigger_condition": raw_payload.get("trigger_condition"),
        "invalidation_condition": raw_payload.get("invalidation_condition"),
        "next_review_point": raw_payload.get("next_review_point"),
        "technical_analysis": report.technical_analysis,
        "fundamental_news": report.fundamental_news,
        "news_summary": raw_payload.get("news_summary") or report.fundamental_news,
        "fundamental_analysis": raw_payload.get("fundamental_analysis"),
        "macro_risk_note": raw_payload.get("macro_risk_note"),
        "add_on_trigger": raw_payload.get("add_on_trigger"),
        "action_advice": report.action_advice,
        "investment_horizon": report.investment_horizon,
        "confidence_level": report.confidence_level,
        "immediate_action": report.immediate_action,
        "target_price": report.target_price,
        "target_price_1": raw_payload.get("target_price_1"),
        "target_price_2": raw_payload.get("target_price_2"),
        "stop_loss_price": report.stop_loss_price,
        "max_position_pct": raw_payload.get("max_position_pct"),
        "entry_zone": report.entry_zone or extract_entry_zone_fallback(report.action_advice),
        "entry_price_low": report.entry_price_low
        if report.entry_price_low is not None
        else extract_entry_prices_fallback(report.action_advice)[0],
        "entry_price_high": report.entry_price_high
        if report.entry_price_high is not None
        else extract_entry_prices_fallback(report.action_advice)[1],
        "rr_ratio": rr_ratio or report.rr_ratio,
        "bull_case": raw_payload.get("bull_case"),
        "base_case": raw_payload.get("base_case"),
        "bear_case": raw_payload.get("bear_case"),
        "scenario_tags": report.scenario_tags,
        "thought_process": report.thought_process,
        "is_cached": True,
        "model_used": report.model_used,
        "report_scope": getattr(report, "report_scope", None),
        "created_at": report.created_at,
        "history_price": history_price,
    }
