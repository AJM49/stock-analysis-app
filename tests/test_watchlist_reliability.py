from datetime import date
from datetime import timedelta

import pandas as pd

from controllers.watchlist_controller import (
    build_watchlist_data_health,
    build_watchlist_reliability,
    build_watchlist_reliability_data,
    classify_watchlist_freshness,
)


def test_watchlist_price_is_fresh_within_seven_days():
    age_days, freshness = (
        classify_watchlist_freshness(
            date.today() - timedelta(days=3)
        )
    )

    assert age_days == 3
    assert freshness == "Fresh"


def test_watchlist_price_is_stale_after_seven_days():
    age_days, freshness = (
        classify_watchlist_freshness(
            date.today() - timedelta(days=8)
        )
    )

    assert age_days == 8
    assert freshness == "Stale"


def test_watchlist_missing_market_date_is_missing():
    age_days, freshness = (
        classify_watchlist_freshness(None)
    )

    assert age_days is None
    assert freshness == "Missing"


def test_watchlist_data_health_counts_states():
    metrics_df = pd.DataFrame(
        [
            {"Data Freshness": "Fresh"},
            {"Data Freshness": "Fresh"},
            {"Data Freshness": "Stale"},
            {"Data Freshness": "Missing"},
        ]
    )

    health = build_watchlist_data_health(
        metrics_df
    )

    assert health["total_tickers"] == 4
    assert health["fresh_count"] == 2
    assert health["stale_count"] == 1
    assert health["missing_count"] == 1
    assert health["coverage_pct"] == 75.0
    assert health["freshness_pct"] == 50.0
    assert health["quality_score"] == 62.5
    assert health["quality_status"] == "Fair"


def test_watchlist_reliability_matches_portfolio_contract():
    reliability = build_watchlist_reliability(
        {
            "total_tickers": 10,
            "quality_status": "Fair",
            "quality_score": 65.0,
            "coverage_pct": 80.0,
            "freshness_pct": 50.0,
        }
    )

    assert reliability["status"] == "Use With Caution"
    assert reliability["severity"] == "warning"


def test_watchlist_reliability_data_adds_freshness_columns():
    rows = [
        {
            "Ticker": "AAPL",
            "Latest Market Date": date.today(),
        },
        {
            "Ticker": "OLD",
            "Latest Market Date": (
                date.today()
                - timedelta(days=20)
            ),
        },
    ]

    metrics_df = (
        build_watchlist_reliability_data(
            rows
        )
    )

    assert list(
        metrics_df["Data Freshness"]
    ) == [
        "Fresh",
        "Stale",
    ]
