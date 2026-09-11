from services.watchlist_research_service import (
    build_watchlist_research_priorities,
    sort_watchlist_research_priorities,
)


def test_missing_cache_is_high_priority():
    items = build_watchlist_research_priorities(
        [
            {
                "Ticker": "ADVB",
                "Cache Status": "Unavailable",
                "Age Days": None,
                "Daily Change %": None,
            }
        ]
    )

    assert len(items) == 1
    assert items[0]["ticker"] == "ADVB"
    assert items[0]["priority"] == "high"
    assert items[0]["reason"] == (
        "Missing cached market data"
    )


def test_stale_cache_is_medium_priority():
    items = build_watchlist_research_priorities(
        [
            {
                "Ticker": "NOW",
                "Cache Status": "Cached",
                "Age Days": 12,
                "Daily Change %": 1.25,
            }
        ]
    )

    assert len(items) == 1
    assert items[0]["ticker"] == "NOW"
    assert items[0]["priority"] == "medium"
    assert "12 days old" in items[0]["reason"]


def test_large_daily_move_is_high_priority():
    items = build_watchlist_research_priorities(
        [
            {
                "Ticker": "TSLA",
                "Cache Status": "Cached",
                "Age Days": 1,
                "Daily Change %": -6.75,
            }
        ]
    )

    assert len(items) == 1
    assert items[0]["ticker"] == "TSLA"
    assert items[0]["priority"] == "high"
    assert "-6.75%" in items[0]["reason"]


def test_healthy_metric_has_no_priority_item():
    items = build_watchlist_research_priorities(
        [
            {
                "Ticker": "AAPL",
                "Cache Status": "Cached",
                "Age Days": 1,
                "Daily Change %": 1.50,
            }
        ]
    )

    assert items == []


def test_priorities_sort_high_before_medium():
    items = [
        {
            "ticker": "NOW",
            "priority": "medium",
            "reason": "Stale market data",
        },
        {
            "ticker": "TSLA",
            "priority": "high",
            "reason": "Large daily move",
        },
        {
            "ticker": "ADVB",
            "priority": "high",
            "reason": "Missing cached market data",
        },
    ]

    sorted_items = (
        sort_watchlist_research_priorities(
            items
        )
    )

    assert [
        item["priority"]
        for item in sorted_items
    ] == [
        "high",
        "high",
        "medium",
    ]

    assert [
        item["ticker"]
        for item in sorted_items
    ] == [
        "ADVB",
        "TSLA",
        "NOW",
    ]
