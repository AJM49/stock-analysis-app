import pandas as pd

from portfolio import calculate_portfolio_data_health


def test_portfolio_data_health_counts_states():
    portfolio_df = pd.DataFrame(
        [
            {"Ticker": "AAPL", "Price Freshness": "Fresh"},
            {"Ticker": "MSFT", "Price Freshness": "Fresh"},
            {"Ticker": "NVDA", "Price Freshness": "Stale"},
            {"Ticker": "ADVB", "Price Freshness": "Missing"},
        ]
    )

    health = calculate_portfolio_data_health(
        portfolio_df
    )

    assert health["total_positions"] == 4
    assert health["fresh_count"] == 2
    assert health["stale_count"] == 1
    assert health["missing_count"] == 1
    assert health["available_count"] == 3


def test_portfolio_data_health_calculates_coverage():
    portfolio_df = pd.DataFrame(
        [
            {"Price Freshness": "Fresh"},
            {"Price Freshness": "Stale"},
            {"Price Freshness": "Missing"},
            {"Price Freshness": "Missing"},
        ]
    )

    health = calculate_portfolio_data_health(
        portfolio_df
    )

    assert health["coverage_pct"] == 50.0
    assert health["freshness_pct"] == 25.0


def test_portfolio_data_health_scores_stale_below_fresh():
    portfolio_df = pd.DataFrame(
        [
            {"Price Freshness": "Fresh"},
            {"Price Freshness": "Stale"},
            {"Price Freshness": "Missing"},
            {"Price Freshness": "Missing"},
        ]
    )

    health = calculate_portfolio_data_health(
        portfolio_df
    )

    assert health["quality_score"] == 37.5
    assert health["quality_status"] == "Poor"


def test_portfolio_data_health_handles_empty_dataframe():
    health = calculate_portfolio_data_health(
        pd.DataFrame()
    )

    assert health["total_positions"] == 0
    assert health["coverage_pct"] == 0.0
    assert health["quality_status"] == "No Data"
