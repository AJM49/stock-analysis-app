from datetime import date

from services.watchlist_signal_service import (
    build_watchlist_research_signals,
    classify_daily_move_signal,
    classify_research_priority,
    classify_watchlist_data_freshness,
)


def test_watchlist_freshness_classifies_recent_cache():
    result = classify_watchlist_data_freshness(
        "Cached",
        date(2026, 8, 18),
        today=date(2026, 8, 20),
    )

    assert result["age_days"] == 2
    assert result["freshness"] == "Fresh"


def test_watchlist_freshness_classifies_stale_cache():
    result = classify_watchlist_data_freshness(
        "Cached",
        date(2026, 8, 1),
        today=date(2026, 8, 20),
    )

    assert result["age_days"] == 19
    assert result["freshness"] == "Stale"


def test_watchlist_freshness_classifies_missing_cache():
    result = classify_watchlist_data_freshness(
        "Unavailable",
        None,
        today=date(2026, 8, 20),
    )

    assert result["age_days"] is None
    assert result["freshness"] == "Missing"


def test_daily_move_signals():
    assert classify_daily_move_signal(
        4.2
    ) == "Sharp Move Up"

    assert classify_daily_move_signal(
        1.4
    ) == "Move Up"

    assert classify_daily_move_signal(
        0.2
    ) == "Quiet"

    assert classify_daily_move_signal(
        -1.7
    ) == "Move Down"

    assert classify_daily_move_signal(
        -4.0
    ) == "Sharp Move Down"


def test_stale_data_receives_high_research_priority():
    priority = classify_research_priority(
        "Stale",
        0.1,
    )

    assert priority == "High"


def test_large_fresh_move_receives_high_priority():
    priority = classify_research_priority(
        "Fresh",
        -3.5,
    )

    assert priority == "High"


def test_signal_builder_enriches_watchlist_rows():
    rows = [
        {
            "Ticker": "AAPL",
            "Daily Change %": 3.5,
            "Latest Market Date": date(
                2026,
                8,
                19,
            ),
            "Cache Status": "Cached",
        },
        {
            "Ticker": "OLD",
            "Daily Change %": 0.2,
            "Latest Market Date": date(
                2026,
                7,
                1,
            ),
            "Cache Status": "Cached",
        },
    ]

    signals = build_watchlist_research_signals(
        rows,
        today=date(2026, 8, 20),
    )

    assert signals[0][
        "Data Freshness"
    ] == "Fresh"

    assert signals[0][
        "Move Signal"
    ] == "Sharp Move Up"

    assert signals[0][
        "Research Priority"
    ] == "High"

    assert signals[1][
        "Data Freshness"
    ] == "Stale"

    assert signals[1][
        "Research Priority"
    ] == "High"
