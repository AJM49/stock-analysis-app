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
            "Daily Change %": 0.5,
        },
        {
            "Ticker": "NOW",
            "Cache Status": "Cached",
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
