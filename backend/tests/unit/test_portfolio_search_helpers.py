from app.application.portfolio.search_helpers import (
    build_provider_order,
    build_search_candidates,
    infer_search_market_hint,
)


def test_build_search_candidates_for_us_stock():
    assert build_search_candidates("asts") == ["ASTS"]


def test_build_search_candidates_for_hk_stock():
    assert build_search_candidates("700") == ["700", "0700.HK", "00700.HK"]


def test_build_search_candidates_for_domestic_six_digit_code():
    assert build_search_candidates("510300") == ["510300", "510300.SZ", "510300.SS"]


def test_build_search_candidates_normalizes_sh_suffix():
    assert build_search_candidates("600519.SH") == ["600519.SH", "600519.SS"]


def test_build_provider_order_respects_user_preference():
    assert build_provider_order("YFINANCE") == ["YFINANCE", "AKSHARE"]
    assert build_provider_order("AKSHARE") == ["AKSHARE", "YFINANCE"]


def test_infer_search_market_hint():
    assert infer_search_market_hint("赛力斯") == "CN_TEXT"
    assert infer_search_market_hint("510300") == "CN_CODE"
    assert infer_search_market_hint("700") == "HK_CODE"
    assert infer_search_market_hint("00700.HK") == "CN_CODE"
    assert infer_search_market_hint("Broadcom") == "US_CODE"
    assert infer_search_market_hint("ASTS") == "US_CODE"


def test_build_provider_order_prefers_akshare_for_cn_queries():
    assert build_provider_order("YFINANCE", "赛力斯") == ["AKSHARE", "YFINANCE"]
    assert build_provider_order("YFINANCE", "510300") == ["AKSHARE", "YFINANCE"]
    assert build_provider_order("YFINANCE", "00700.HK") == ["AKSHARE", "YFINANCE"]


def test_build_provider_order_prefers_yfinance_for_us_queries():
    assert build_provider_order("AKSHARE", "Broadcom") == ["YFINANCE", "AKSHARE"]
    assert build_provider_order("AKSHARE", "ASTS") == ["YFINANCE", "AKSHARE"]
