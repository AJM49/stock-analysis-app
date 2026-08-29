from datetime import date, timedelta

from services.watchlist_research_service import (
    build_watchlist_research_queue,
    classify_watchlist_research_priority,
)


def test_missing_cache_needs_data():
    result = classify_watchlist_research_priority(
        {
            "Ticker": "ADVB",
            "Cache Status": "Unavailable",
            "Daily Change %": None,
        }
    )

    assert result["research_status"] == "Needs Data"
    assert result["priority"] == 4


def test_large_daily_move_requires_review():
    result = classify_watchlist_research_priority(
        {
            "Ticker": "NOW",
            "Cache Status": "Cached",
            "Latest Market Date": date.today(),
            "Daily Change %": -6.2,
        }
    )

    assert result["research_status"] == "Review Now"
    assert result["priority"] == 3


def test_moderate_daily_move_is_monitor():
    result = classify_watchlist_research_priority(
        {
            "Ticker": "AAPL",
            "Cache Status": "Cached",
            "Latest Market Date": date.today(),
            "Daily Change %": 2.5,
        }
    )

    assert result["research_status"] == "Monitor"
    assert result["priority"] == 2


def test_small_daily_move_is_stable():
    result = classify_watchlist_research_priority(
        {
            "Ticker": "MSFT",
            "Cache Status": "Cached",
            "Latest Market Date": date.today(),
            "Daily Change %": 0.8,
        }
    )

    assert result["research_status"] == "Stable"
    assert result["priority"] == 1


def test_research_queue_sorts_highest_priority_first():
    rows = [
        {
            "Ticker": "MSFT",
            "Cache Status": "Cached",
            "Latest Market Date": date.today(),
            "Daily Change %": 0.5,
        },
        {
            "Ticker": "NOW",
            "Cache Status": "Cached",
            "Latest Market Date": date.today(),
            "Daily Change %": -7.0,
        },
        {
            "Ticker": "ADVB",
            "Cache Status": "Unavailable",
            "Daily Change %": None,
        },
    ]

    queue = build_watchlist_research_queue(
        rows
    )

    assert [
        row["Ticker"]
        for row in queue
    ] == [
        "ADVB",
        "NOW",
        "MSFT",
    ]



def test_stale_cached_market_data_needs_data():
    result = classify_watchlist_research_priority(
        {
            "Ticker": "NVDA",
            "Cache Status": "Cached",
            "Latest Market Date": (
                date.today() - timedelta(days=8)
            ),
            "Daily Change %": -9.0,
        }
    )

    assert result["research_status"] == "Needs Data"
    assert result["priority"] == 4
    assert "8 days old" in result["reason"]


def test_cached_row_without_market_date_needs_data():
    result = classify_watchlist_research_priority(
        {
            "Ticker": "AAPL",
            "Cache Status": "Cached",
            "Daily Change %": 6.0,
        }
    )

    assert result["research_status"] == "Needs Data"
    assert result["priority"] == 4
    assert "freshness could not be determined" in result["reason"]



def test_research_queue_uses_descending_numeric_priority():
    rows = [
        {
            "Ticker": "STABLE",
            "Cache Status": "Cached",
            "Latest Market Date": date.today(),
            "Daily Change %": 0.5,
        },
        {
            "Ticker": "REVIEW",
            "Cache Status": "Cached",
            "Latest Market Date": date.today(),
            "Daily Change %": 6.0,
        },
        {
            "Ticker": "MISSING",
            "Cache Status": "Missing",
            "Latest Market Date": None,
            "Daily Change %": None,
        },
    ]

    queue = build_watchlist_research_queue(rows)

    assert [
        row["Research Priority"]
        for row in queue
    ] == [4, 3, 1]

    assert [
        row["Research Status"]
        for row in queue
    ] == [
        "Needs Data",
        "Review Now",
        "Stable",
    ]
