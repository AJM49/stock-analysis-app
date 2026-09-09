from datetime import date

from features.watchlist import (
    build_prioritized_watchlist,
    classify_watchlist_priority,
)


TEST_DATE = date(2026, 9, 9)


def test_missing_cache_is_high_priority():
    priority = classify_watchlist_priority(
        {
            "Ticker": "ADVB",
            "Cache Status": "Unavailable",
            "Latest Market Date": None,
            "Daily Change %": 0.0,
        },
        today=TEST_DATE,
    )

    assert priority == "High"


def test_stale_market_data_is_high_priority():
    priority = classify_watchlist_priority(
        {
            "Ticker": "NVDA",
            "Cache Status": "Cached",
            "Latest Market Date": "2026-08-20",
            "Daily Change %": 1.0,
        },
        today=TEST_DATE,
    )

    assert priority == "High"


def test_large_daily_move_is_medium_priority():
    priority = classify_watchlist_priority(
        {
            "Ticker": "AAPL",
            "Cache Status": "Cached",
            "Latest Market Date": "2026-09-08",
            "Daily Change %": -4.5,
        },
        today=TEST_DATE,
    )

    assert priority == "Medium"


def test_normal_cached_ticker_is_low_priority():
    priority = classify_watchlist_priority(
        {
            "Ticker": "MSFT",
            "Cache Status": "Cached",
            "Latest Market Date": "2026-09-08",
            "Daily Change %": 0.8,
        },
        today=TEST_DATE,
    )

    assert priority == "Low"


def test_watchlist_priority_order_is_deterministic():
    rows = [
        {
            "Ticker": "MSFT",
            "Cache Status": "Cached",
            "Latest Market Date": "2026-09-08",
            "Daily Change %": 0.5,
        },
        {
            "Ticker": "AAPL",
            "Cache Status": "Cached",
            "Latest Market Date": "2026-09-08",
            "Daily Change %": 4.0,
        },
        {
            "Ticker": "ZZZZ",
            "Cache Status": "Unavailable",
            "Latest Market Date": None,
            "Daily Change %": 0.0,
        },
        {
            "Ticker": "AAAA",
            "Cache Status": "Unavailable",
            "Latest Market Date": None,
            "Daily Change %": 0.0,
        },
    ]

    result = build_prioritized_watchlist(
        rows,
        today=TEST_DATE,
    )

    assert result["Ticker"].tolist() == [
        "AAAA",
        "ZZZZ",
        "AAPL",
        "MSFT",
    ]

    assert result[
        "Research Priority"
    ].tolist() == [
        "High",
        "High",
        "Medium",
        "Low",
    ]


def test_watchlist_order_does_not_depend_on_input_order():
    rows = [
        {
            "Ticker": "MSFT",
            "Cache Status": "Cached",
            "Latest Market Date": "2026-09-08",
            "Daily Change %": 0.5,
        },
        {
            "Ticker": "ZZZZ",
            "Cache Status": "Unavailable",
            "Latest Market Date": None,
            "Daily Change %": 0.0,
        },
        {
            "Ticker": "AAAA",
            "Cache Status": "Unavailable",
            "Latest Market Date": None,
            "Daily Change %": 0.0,
        },
        {
            "Ticker": "AAPL",
            "Cache Status": "Cached",
            "Latest Market Date": "2026-09-08",
            "Daily Change %": 4.0,
        },
    ]

    forward = build_prioritized_watchlist(
        rows,
        today=TEST_DATE,
    )

    reversed_result = (
        build_prioritized_watchlist(
            list(reversed(rows)),
            today=TEST_DATE,
        )
    )

    assert forward["Ticker"].tolist() == (
        reversed_result["Ticker"].tolist()
    )


def test_high_priority_filter_returns_only_high_rows():
    rows = [
        {
            "Ticker": "AAPL",
            "Cache Status": "Cached",
            "Latest Market Date": "2026-09-08",
            "Daily Change %": 0.5,
        },
        {
            "Ticker": "ADVB",
            "Cache Status": "Unavailable",
            "Latest Market Date": None,
            "Daily Change %": 0.0,
        },
    ]

    result = build_prioritized_watchlist(
        rows,
        high_priority_only=True,
        today=TEST_DATE,
    )

    assert result["Ticker"].tolist() == [
        "ADVB"
    ]

    assert (
        result["Research Priority"]
        == "High"
    ).all()
