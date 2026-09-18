from datetime import date

from services.watchlist_research_service import (
    build_watchlist_research_queue,
    classify_watchlist_research_priority,
    get_watchlist_market_data_age_days,
)


TODAY = date(2026, 8, 28)


def test_missing_cache_needs_data():
    classification = (
        classify_watchlist_research_priority(
            {
                "Ticker": "MISSING",
                "Cache Status": "Unavailable",
                "Latest Market Date": None,
            },
            today=TODAY,
        )
    )

    assert classification["research_status"] == "Needs Data"
    assert classification["priority"] == 4


def test_old_cached_market_data_needs_data():
    classification = (
        classify_watchlist_research_priority(
            {
                "Ticker": "NOW",
                "Cache Status": "Cached",
                "Latest Market Date": "2026-08-10",
                "Daily Change %": 1.0,
            },
            today=TODAY,
        )
    )

    assert classification["research_status"] == "Needs Data"
    assert classification["priority"] == 4
    assert "18 days old" in classification["reason"]


def test_recent_large_move_requires_review_now():
    classification = (
        classify_watchlist_research_priority(
            {
                "Ticker": "NVDA",
                "Cache Status": "Cached",
                "Latest Market Date": "2026-08-27",
                "Daily Change %": -5.5,
            },
            today=TODAY,
        )
    )

    assert classification["research_status"] == "Review Now"
    assert classification["priority"] == 3


def test_recent_medium_move_is_monitor():
    classification = (
        classify_watchlist_research_priority(
            {
                "Ticker": "MSFT",
                "Cache Status": "Cached",
                "Latest Market Date": "2026-08-27",
                "Daily Change %": 2.5,
            },
            today=TODAY,
        )
    )

    assert classification["research_status"] == "Monitor"
    assert classification["priority"] == 2


def test_recent_small_move_is_stable():
    classification = (
        classify_watchlist_research_priority(
            {
                "Ticker": "AAPL",
                "Cache Status": "Cached",
                "Latest Market Date": "2026-08-27",
                "Daily Change %": 0.5,
            },
            today=TODAY,
        )
    )

    assert classification["research_status"] == "Stable"
    assert classification["priority"] == 1


def test_market_data_age_uses_supplied_today():
    age_days = get_watchlist_market_data_age_days(
        {
            "Latest Market Date": "2026-08-10",
        },
        today=TODAY,
    )

    assert age_days == 18


def test_research_queue_orders_by_priority_then_ticker():
    rows = [
        {
            "Ticker": "AAPL",
            "Cache Status": "Cached",
            "Latest Market Date": "2026-08-27",
            "Daily Change %": 0.5,
        },
        {
            "Ticker": "NOW",
            "Cache Status": "Cached",
            "Latest Market Date": "2026-08-01",
            "Daily Change %": 1.0,
        },
        {
            "Ticker": "NVDA",
            "Cache Status": "Cached",
            "Latest Market Date": "2026-08-27",
            "Daily Change %": -6.0,
        },
        {
            "Ticker": "MSFT",
            "Cache Status": "Cached",
            "Latest Market Date": "2026-08-27",
            "Daily Change %": 2.5,
        },
    ]

    ranked = build_watchlist_research_queue(
        rows,
        today=TODAY,
    )

    assert [
        row["Ticker"]
        for row in ranked
    ] == [
        "NOW",
        "NVDA",
        "MSFT",
        "AAPL",
    ]

    assert [
        row["Research Status"]
        for row in ranked
    ] == [
        "Needs Data",
        "Review Now",
        "Monitor",
        "Stable",
    ]
