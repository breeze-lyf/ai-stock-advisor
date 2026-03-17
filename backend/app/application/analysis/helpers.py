from typing import Any, Optional


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
