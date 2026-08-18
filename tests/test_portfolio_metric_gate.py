from controllers.portfolio_controller import (
    build_portfolio_metric_gate,
)


def test_reliable_portfolio_allows_all_analytics():
    gate = build_portfolio_metric_gate(
        {
            "status": "Reliable",
        }
    )

    assert gate["mode"] == "normal"
    assert gate["show_derived_metrics"] is True
    assert gate["show_risk_analytics"] is True
    assert gate["show_performance_analytics"] is True
    assert gate["show_raw_holdings"] is True


def test_caution_portfolio_keeps_analytics_visible():
    gate = build_portfolio_metric_gate(
        {
            "status": "Use With Caution",
        }
    )

    assert gate["mode"] == "caution"
    assert gate["show_derived_metrics"] is True
    assert gate["show_risk_analytics"] is True
    assert gate["show_performance_analytics"] is True
    assert gate["show_raw_holdings"] is True


def test_insufficient_data_suppresses_derived_analytics():
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


def test_unavailable_data_suppresses_derived_analytics():
    gate = build_portfolio_metric_gate(
        {
            "status": "Unavailable",
        }
    )

    assert gate["mode"] == "unavailable"
    assert gate["show_derived_metrics"] is False
    assert gate["show_risk_analytics"] is False
    assert gate["show_performance_analytics"] is False
    assert gate["show_raw_holdings"] is True
