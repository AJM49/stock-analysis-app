from controllers.portfolio_controller import (
    build_portfolio_analytics_reliability,
    get_portfolio_analytics_render_mode,
    should_render_portfolio_summary_metrics,
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
    assert reliability["analytics_mode"] == "full"
    assert reliability["render_mode"] == "full"
    assert reliability["analytics_mode"] == "full"
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
    assert reliability["analytics_mode"] == "caution"
    assert reliability["render_mode"] == "caution"
    assert reliability["analytics_mode"] == "caution"
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
    assert reliability["analytics_mode"] == "limited"
    assert reliability["render_mode"] == "restricted"
    assert reliability["analytics_mode"] == "limited"
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
    assert reliability["analytics_mode"] == "unavailable"
    assert reliability["render_mode"] == "unavailable"
    assert reliability["analytics_mode"] == "unavailable"
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
