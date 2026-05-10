from datetime import datetime

import pytz

from app.services.scheduler_jobs import _is_market_open_for


def test_us_alert_market_closed_on_sunday_beijing_evening():
    # 2026-05-10 23:25 Beijing is Sunday 11:25 in New York, so US alerts must not fire.
    now_utc = pytz.timezone("Asia/Shanghai").localize(datetime(2026, 5, 10, 23, 25)).astimezone(pytz.utc)

    assert _is_market_open_for("GOOGL", now_utc=now_utc) is False


def test_us_alert_market_open_regular_session():
    now_utc = pytz.timezone("America/New_York").localize(datetime(2026, 5, 11, 10, 0)).astimezone(pytz.utc)

    assert _is_market_open_for("GOOGL", now_utc=now_utc) is True


def test_hk_numeric_ticker_market_hours():
    open_time = pytz.timezone("Asia/Shanghai").localize(datetime(2026, 5, 11, 10, 0)).astimezone(pytz.utc)
    closed_time = pytz.timezone("Asia/Shanghai").localize(datetime(2026, 5, 11, 12, 30)).astimezone(pytz.utc)

    assert _is_market_open_for("00700", now_utc=open_time) is True
    assert _is_market_open_for("00700", now_utc=closed_time) is False
