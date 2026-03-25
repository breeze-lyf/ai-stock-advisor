from types import SimpleNamespace

from app.application.analysis.mappers import serialize_analysis_report


def build_report(**overrides):
    base = {
        "ticker": "ASTS",
        "ai_response_markdown": '{"summary_status":"观察","technical_analysis":"测试"}',
        "sentiment_score": "82",
        "summary_status": "观察",
        "risk_level": "MEDIUM",
        "technical_analysis": "技术面测试",
        "fundamental_news": "消息面测试",
        "action_advice": "继续观察",
        "investment_horizon": None,
        "confidence_level": None,
        "immediate_action": None,
        "target_price": None,
        "stop_loss_price": None,
        "entry_zone": None,
        "entry_price_low": None,
        "entry_price_high": None,
        "rr_ratio": None,
        "scenario_tags": None,
        "thought_process": None,
        "model_used": "test-model",
        "created_at": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_serialize_analysis_report_accepts_numeric_sentiment_string():
    payload = serialize_analysis_report(build_report(sentiment_score="82"))
    assert payload["sentiment_score"] == 82.0


def test_serialize_analysis_report_tolerates_non_numeric_sentiment_string():
    payload = serialize_analysis_report(build_report(sentiment_score="BULLISH"))
    assert payload["sentiment_score"] is None
    assert payload["ticker"] == "ASTS"


def test_serialize_analysis_report_filters_non_dict_json_items():
    payload = serialize_analysis_report(
        build_report(
            scenario_tags=[{"category": "技术形态", "value": "均线纠缠"}, "bad-item"],
            thought_process=[{"step": "观察", "content": "ok"}, "step"],
        )
    )
    assert payload["scenario_tags"] == [{"category": "技术形态", "value": "均线纠缠"}]
    assert payload["thought_process"] == [{"step": "观察", "content": "ok"}]
