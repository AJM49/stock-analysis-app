import pandas as pd

from controllers.portfolio_controller import (
    build_priced_portfolio_analytics_data,
)


def test_priced_portfolio_excludes_missing_prices():
    portfolio_df = pd.DataFrame(
        [
            {
                "Ticker": "MU",
                "Price Status": "Available",
                "Current Value": 1000.0,
            },
            {
                "Ticker": "AWL",
                "Price Status": "Missing",
                "Current Value": 0.0,
            },
        ]
    )

    result = build_priced_portfolio_analytics_data(
        portfolio_df
    )

    assert result["Ticker"].tolist() == ["MU"]


def test_priced_portfolio_keeps_stale_available_prices():
    portfolio_df = pd.DataFrame(
        [
            {
                "Ticker": "MU",
                "Price Status": "Available",
                "Price Freshness": "Stale",
            },
        ]
    )

    result = build_priced_portfolio_analytics_data(
        portfolio_df
    )

    assert result["Ticker"].tolist() == ["MU"]


def test_priced_portfolio_handles_empty_input():
    result = build_priced_portfolio_analytics_data(
        pd.DataFrame()
    )

    assert result.empty
