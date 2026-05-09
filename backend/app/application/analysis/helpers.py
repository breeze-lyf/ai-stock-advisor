from typing import Any, Optional


SHARED_SCOPE = "shared_stock_analysis"


def is_error_report(report) -> bool:
    """Check if an analysis report has an AI error response."""
    raw = (getattr(report, "ai_response_markdown", None) or "").strip()
    return raw.startswith("**Error**")


def pick_shared_scope_report(reports: list) -> Optional[Any]:
    """从候选报告中挑选最佳共享范围报告，优先返回非 error 报告。"""
    if not reports:
        return None
    first_shared = None
    for report in reports:
        scope = getattr(report, "report_scope", None)
        is_shared = scope == SHARED_SCOPE
        if not is_shared:
            snapshot = getattr(report, "input_context_snapshot", None) or {}
            is_shared = isinstance(snapshot, dict) and snapshot.get("analysis_scope") == "stock_shared"
        if is_shared:
            if first_shared is None:
                first_shared = report
            if not is_error_report(report):
                return report
    return first_shared


async def find_latest_shared_report(repo, ticker: str, preferred_model: str | None = None):
    """跨模型查询 ticker 的最新非 error 共享报告。"""
    candidates = await repo.get_latest_reports_for_ticker(ticker, limit=10, model_used=preferred_model)
    report = pick_shared_scope_report(candidates)
    if report:
        return report
    if preferred_model:
        fallback_candidates = await repo.get_latest_reports_for_ticker(ticker, limit=10)
        return pick_shared_scope_report(fallback_candidates)
    return None


def extract_entry_prices_fallback(action_advice: str) -> tuple[Optional[float], Optional[float]]:
    if not action_advice:
        return None, None

    import re

    zone_match = re.search(r"(\d+\.?\d*)\s*(?:-|至|~)\s*(\d+\.?\d*)", action_advice)
    if zone_match:
        vals = sorted([float(zone_match.group(1)), float(zone_match.group(2))])
        return vals[0], vals[1]

    price_match = re.search(
        r"(?:附近|点位|位|价|在|于)\s*(\d+\.?\d*)|(\d+\.?\d*)\s*(?:元)?\s*(?:附近|左右|点位)",
        action_advice,
    )
    if price_match:
        val_str = price_match.group(1) or price_match.group(2)
        val = float(val_str)
        return val, val

    return None, None


def extract_entry_zone_fallback(action_advice: str) -> Optional[str]:
    low, high = extract_entry_prices_fallback(action_advice)
    if low and high:
        if low == high:
            return f"Near {low}"
        return f"{low} - {high}"
    return None


def to_str(val: Any):
    if val is None:
        return None
    if isinstance(val, (list, dict)):
        try:
            return "\n".join(str(item) for item in val) if isinstance(val, list) else str(val)
        except Exception:
            return str(val)
    return str(val)


def to_float(val: Any):
    try:
        if val is None or val == "":
            return None
        return float(val)
    except (ValueError, TypeError):
        return None
