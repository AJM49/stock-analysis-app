from datetime import date

import pandas as pd

from features.watchlist import (
    classify_watchlist_research_status,
    rank_watchlist_research_queue,
)


TODAY = date(2026, 8, 28)


def test_missing_cache_needs_attention():
    status, age_days = (
        classify_watchlist_research_status(
            {
                "Cache Status": "Unavailable",
                "Latest Market Date": None,
            },
            today=TODAY,
        )
    )

    assert status == "Needs Attention"
    assert age_days is None


def test_old_cached_market_data_is_stale():
    status, age_days = (
        classify_watchlist_research_status(
            {
                "Cache Status": "Cached",
                "Latest Market Date": "2026-08-10",
            },
            today=TODAY,
        )
    )

    assert status == "Stale"
    assert age_days == 18


def test_recent_cached_market_data_is_ready():
    status, age_days = (
        classify_watchlist_research_status(
            {
                "Cache Status": "Cached",
                "Latest Market Date": "2026-08-25",
            },
            today=TODAY,
        )
    )

    assert status == "Ready"
    assert age_days == 3


def test_research_queue_orders_attention_stale_ready():
    metrics_df = pd.DataFrame(
        [
            {
                "Ticker": "AAPL",
                "Cache Status": "Cached",
                "Latest Market Date": "2026-08-27",
            },
            {
                "Ticker": "NOW",
                "Cache Status": "Cached",
                "Latest Market Date": "2026-08-01",
            },
            {
                "Ticker": "MISSING",
                "Cache Status": "Unavailable",
                "Latest Market Date": None,
            },
            {
                "Ticker": "MSFT",
                "Cache Status": "Cached",
                "Latest Market Date": "2026-08-24",
            },
        ]
    )

    ranked_df = rank_watchlist_research_queue(
        metrics_df,
        today=TODAY,
    )

    assert ranked_df["Ticker"].tolist() == [
        "MISSING",
        "NOW",
        "MSFT",
        "AAPL",
    ]

    assert ranked_df[
        "Research Status"
    ].tolist() == [
        "Needs Attention",
        "Stale",
        "Ready",
        "Ready",
    ]
