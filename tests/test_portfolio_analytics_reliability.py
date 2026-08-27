from controllers.portfolio_controller import (
    build_portfolio_analytics_reliability,
    get_portfolio_analytics_render_mode,
    should_render_portfolio_summary_metrics,
    build_portfolio_metric_gate,
    build_priced_portfolio_analytics_data,
)


def test_good_portfolio_health_is_reliable():
    reliability = build_portfolio_analytics_reliability(
        {
            "total_positions": 10,
            "quality_status": "Good",
            "quality_score": 82.0,
            "coverage_pct": 100.0,
            "freshness_pct": 80.0,
        }
    )

    assert reliability["status"] == "Reliable"
    assert reliability["severity"] == "success"
    assert reliability["decision_ready"] is True
    assert reliability["render_mode"] == "full"
    assert reliability["display_mode"] == "full"


def test_fair_portfolio_health_requires_caution():
    reliability = build_portfolio_analytics_reliability(
        {
            "total_positions": 14,
            "quality_status": "Fair",
            "quality_score": 64.3,
            "coverage_pct": 71.4,
            "freshness_pct": 57.1,
        }
    )

    assert reliability["status"] == "Use With Caution"
    assert reliability["severity"] == "warning"
    assert reliability["decision_ready"] is False
    assert reliability["render_mode"] == "caution"
    assert reliability["display_mode"] == "caution"


def test_poor_portfolio_health_is_insufficient():
    reliability = build_portfolio_analytics_reliability(
        {
            "total_positions": 10,
            "quality_status": "Poor",
            "quality_score": 40.0,
            "coverage_pct": 50.0,
            "freshness_pct": 30.0,
        }
    )

    assert reliability["status"] == "Insufficient Data"
    assert reliability["severity"] == "error"
    assert reliability["decision_ready"] is False
    assert reliability["render_mode"] == "restricted"
    assert reliability["display_mode"] == "restricted"


def test_empty_portfolio_health_is_unavailable():
    reliability = build_portfolio_analytics_reliability(
        {
            "total_positions": 0,
            "quality_status": "No Data",
            "quality_score": 0.0,
            "coverage_pct": 0.0,
            "freshness_pct": 0.0,
        }
    )

    assert reliability["status"] == "Unavailable"
    assert reliability["severity"] == "info"
    assert reliability["decision_ready"] is False
    assert reliability["render_mode"] == "unavailable"
    assert reliability["display_mode"] == "unavailable"



def test_reliable_analytics_use_full_render_mode():
    assert get_portfolio_analytics_render_mode(
        {
            "status": "Reliable",
        }
    ) == "full"


def test_caution_analytics_use_caution_render_mode():
    assert get_portfolio_analytics_render_mode(
        {
            "status": "Use With Caution",
        }
    ) == "caution"


def test_insufficient_analytics_use_limited_mode():
    assert get_portfolio_analytics_render_mode(
        {
            "status": "Insufficient Data",
        }
    ) == "restricted"


def test_unavailable_analytics_use_unavailable_mode():
    assert get_portfolio_analytics_render_mode(
        {
            "status": "Unavailable",
        }
    ) == "unavailable"



def test_reliable_analytics_render_summary_metrics():
    assert should_render_portfolio_summary_metrics(
        {"status": "Reliable"}
    ) is True


def test_caution_analytics_render_summary_metrics():
    assert should_render_portfolio_summary_metrics(
        {"status": "Use With Caution"}
    ) is True


def test_insufficient_analytics_suppress_summary_metrics():
    assert should_render_portfolio_summary_metrics(
        {"status": "Insufficient Data"}
    ) is False



def test_insufficient_data_gate_suppresses_derived_analytics():
    gate = build_portfolio_metric_gate(
        {
            "status": "Insufficient Data",
        }
    )

    assert gate["mode"] == "restricted"
    assert gate["show_derived_metrics"] is False
    assert gate["show_risk_analytics"] is False
    assert gate["show_performance_analytics"] is False
    assert gate["show_raw_holdings"] is True


def test_caution_gate_keeps_derived_analytics_visible():
    gate = build_portfolio_metric_gate(
        {
            "status": "Use With Caution",
        }
    )

    assert gate["mode"] == "caution"
    assert gate["show_derived_metrics"] is True
    assert gate["show_raw_holdings"] is True


def test_priced_analytics_exclude_missing_price_positions():
    import pandas as pd

    portfolio_df = pd.DataFrame(
        [
            {
                "Ticker": "AAPL",
                "Price Status": "Available",
            },
            {
                "Ticker": "ADVB",
                "Price Status": "Missing",
            },
            {
                "Ticker": "MSFT",
                "Price Status": "Available",
            },
        ]
    )

    priced_df = build_priced_portfolio_analytics_data(
        portfolio_df
    )

    assert priced_df["Ticker"].tolist() == [
        "AAPL",
        "MSFT",
    ]



def test_missing_reliability_fails_closed():
    from controllers.portfolio_controller import (
        build_portfolio_metric_gate,
        build_portfolio_render_policy,
    )

    policy = build_portfolio_render_policy(None)
    gate = build_portfolio_metric_gate(None)

    assert policy["mode"] == "unavailable"
    assert policy["show_derived_analytics"] is False
    assert policy["show_raw_holdings"] is True
    assert policy["show_caution"] is True

    assert gate["show_derived_metrics"] is False
    assert gate["show_risk_analytics"] is False
    assert gate["show_performance_analytics"] is False
    assert gate["show_raw_holdings"] is True
