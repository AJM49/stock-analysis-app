from datetime import date
from datetime import timedelta
from types import SimpleNamespace

from features.dashboard import build_dashboard_attention_items


def test_attention_reports_missing_cache():
    metrics = [
        {
            "Ticker": "AAPL",
            "Cache Status": "Cached",
            "Latest Market Date": str(date.today()),
        },
        {
            "Ticker": "XYZ",
            "Cache Status": "Unavailable",
            "Latest Market Date": None,
        },
    ]

    items = build_dashboard_attention_items(
        metrics,
        None,
    )

    titles = [item["title"] for item in items]

    assert "Missing watchlist cache" in titles


def test_attention_reports_stale_market_data():
    stale_date = (
        date.today() - timedelta(days=10)
    )

    metrics = [
        {
            "Ticker": "NOW",
            "Cache Status": "Cached",
            "Latest Market Date": str(stale_date),
        }
    ]

    snapshot = SimpleNamespace(
        snapshot_date=date.today(),
        risk_level="Low Risk",
    )

    items = build_dashboard_attention_items(
        metrics,
        snapshot,
    )

    titles = [item["title"] for item in items]

    assert "Stale watchlist market data" in titles


def test_attention_reports_high_portfolio_risk():
    metrics = []

    snapshot = SimpleNamespace(
        snapshot_date=date.today(),
        risk_level="High Risk",
    )

    items = build_dashboard_attention_items(
        metrics,
        snapshot,
    )

    titles = [item["title"] for item in items]

    assert (
        "Portfolio risk requires attention"
        in titles
    )


def test_attention_reports_stale_snapshot():
    snapshot = SimpleNamespace(
        snapshot_date=(
            date.today()
            - timedelta(days=12)
        ),
        risk_level="Low Risk",
    )

    items = build_dashboard_attention_items(
        [],
        snapshot,
    )

    titles = [item["title"] for item in items]

    assert "Portfolio snapshot stale" in titles


def test_attention_is_empty_when_data_is_healthy():
    metrics = [
        {
            "Ticker": "AAPL",
            "Cache Status": "Cached",
            "Latest Market Date": str(date.today()),
        }
    ]

    snapshot = SimpleNamespace(
        snapshot_date=date.today(),
        risk_level="Low Risk",
    )

    items = build_dashboard_attention_items(
        metrics,
        snapshot,
    )

    assert items == []
