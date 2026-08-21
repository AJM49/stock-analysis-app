from services.watchlist_health_service import (
    build_watchlist_data_health,
)


def test_watchlist_health_counts_cache_coverage():
    rows = [
        {"Ticker": "AAPL", "Cache Status": "Cached"},
        {"Ticker": "MSFT", "Cache Status": "Cached"},
        {"Ticker": "ADVB", "Cache Status": "Unavailable"},
        {"Ticker": "HL", "Cache Status": "Unavailable"},
    ]

    health = build_watchlist_data_health(rows)

    assert health["total_count"] == 4
    assert health["cached_count"] == 2
    assert health["unavailable_count"] == 2
    assert health["coverage_pct"] == 50.0


def test_watchlist_health_rates_good_coverage():
    rows = [
        {"Cache Status": "Cached"},
        {"Cache Status": "Cached"},
        {"Cache Status": "Cached"},
        {"Cache Status": "Unavailable"},
    ]

    health = build_watchlist_data_health(rows)

    assert health["coverage_pct"] == 75.0
    assert health["quality_status"] == "Good"


def test_watchlist_health_handles_empty_rows():
    health = build_watchlist_data_health([])

    assert health["total_count"] == 0
    assert health["coverage_pct"] == 0.0
    assert health["quality_status"] == "No Data"
