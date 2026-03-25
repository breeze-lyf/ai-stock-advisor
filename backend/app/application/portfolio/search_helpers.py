from __future__ import annotations
import re


def build_search_candidates(query: str) -> list[str]:
    normalized = (query or "").strip().upper()
    if not normalized:
        return []

    candidates: list[str] = []

    def add(value: str) -> None:
        if value and value not in candidates:
            candidates.append(value)

    add(normalized)

    if normalized.endswith(".HK"):
        code = normalized[:-3]
        if code.isdigit():
            add(f"{code.zfill(4)}.HK")
            add(f"{code.zfill(5)}.HK")
        return candidates

    if normalized.endswith(".SH"):
        add(f"{normalized[:-3]}.SS")
        return candidates

    if normalized.isdigit():
        if len(normalized) <= 5:
            add(f"{normalized.zfill(4)}.HK")
            add(f"{normalized.zfill(5)}.HK")
        elif len(normalized) == 6:
            add(f"{normalized}.SZ")
            add(f"{normalized}.SS")
        return candidates

    return candidates


def infer_search_market_hint(query: str) -> str:
    raw = (query or "").strip()
    normalized = raw.upper()
    if not normalized:
        return "UNKNOWN"

    if re.search(r"[\u4e00-\u9fff]", raw):
        return "CN_TEXT"

    if normalized.endswith((".SZ", ".SS", ".SH", ".HK")):
        return "CN_CODE"

    if normalized.isdigit() and len(normalized) == 6:
        return "CN_CODE"

    if normalized.isdigit() and len(normalized) <= 5:
        return "HK_CODE"

    if re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", normalized):
        return "US_CODE"

    if re.search(r"[A-Z]", normalized):
        return "US_TEXT"

    return "UNKNOWN"


def build_provider_order(preferred_source: str | None, query: str | None = None) -> list[str]:
    hint = infer_search_market_hint(query or "")
    if hint in {"CN_TEXT", "CN_CODE", "HK_CODE"}:
        return ["AKSHARE", "YFINANCE"]
    if hint in {"US_TEXT", "US_CODE"}:
        return ["YFINANCE", "AKSHARE"]

    preferred = (preferred_source or "AKSHARE").upper()
    if preferred == "YFINANCE":
        return ["YFINANCE", "AKSHARE"]
    return ["AKSHARE", "YFINANCE"]
