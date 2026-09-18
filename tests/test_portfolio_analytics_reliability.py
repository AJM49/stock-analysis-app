from controllers.portfolio_controller import (
    build_portfolio_analytics_reliability,
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
