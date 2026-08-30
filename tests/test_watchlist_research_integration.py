from services.watchlist_research_service import (
    build_watchlist_research_queue,
)
from services.watchlist_signal_service import (
    build_watchlist_research_signals,
)


def test_watchlist_research_pipeline_produces_ui_columns():
    metric_rows = [
        {
            "Ticker": "AAPL",
            "Latest Close": 200.0,
            "Daily Change %": 6.0,
            "Latest Market Date": "2026-08-30",
            "Cached Rows": 100,
            "Cache Status": "Cached",
        }
    ]

    signal_rows = build_watchlist_research_signals(
        metric_rows
    )

    research_rows = build_watchlist_research_queue(
        signal_rows
    )

    assert len(research_rows) == 1

    row = research_rows[0]

    assert "Research Status" in row
    assert "Research Priority" in row
    assert "Research Reason" in row
    assert row["Research Status"] == "Review Now"
    assert row["Research Priority"] == 3
