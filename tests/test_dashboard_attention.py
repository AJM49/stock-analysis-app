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



def test_attention_items_are_sorted_by_priority():
    old_date = date.today() - timedelta(days=20)

    metrics = [
        {
            "Ticker": "STALE",
            "Cache Status": "Cached",
            "Latest Market Date": str(old_date),
        },
        {
            "Ticker": "MISSING",
            "Cache Status": "Unavailable",
            "Latest Market Date": None,
        },
    ]

    snapshot = SimpleNamespace(
        snapshot_date=old_date,
        risk_level="High Risk",
    )

    items = build_dashboard_attention_items(
        metrics,
        snapshot,
    )

    priorities = [
        item["priority"]
        for item in items
    ]

    assert priorities == [
        "critical",
        "high",
        "medium",
        "low",
    ]



def test_attention_reports_missing_portfolio_prices():
    import pandas as pd

    portfolio_df = pd.DataFrame(
        [
            {
                "Ticker": "AAPL",
                "Price Status": "Available",
            },
            {
                "Ticker": "ADVB",
                "Price Status": "Missing",
            },
            {
                "Ticker": "HL",
                "Price Status": "Missing",
            },
        ]
    )

    snapshot = SimpleNamespace(
        snapshot_date=date.today(),
        risk_level="Low Risk",
    )

    items = build_dashboard_attention_items(
        [],
        snapshot,
        portfolio_df,
    )

    alert = next(
        item
        for item in items
        if item["title"] == "Missing portfolio prices"
    )

    assert alert["priority"] == "high"
    assert alert["details"] == ["ADVB", "HL"]



def test_attention_reports_stale_portfolio_prices():
    import pandas as pd

    portfolio_df = pd.DataFrame(
        [
            {
                "Ticker": "AAPL",
                "Price Status": "Available",
                "Price Freshness": "Fresh",
                "Price Age Days": 1,
            },
            {
                "Ticker": "NVDA",
                "Price Status": "Available",
                "Price Freshness": "Stale",
                "Price Age Days": 12,
            },
        ]
    )

    snapshot = SimpleNamespace(
        snapshot_date=date.today(),
        risk_level="Low Risk",
    )

    items = build_dashboard_attention_items(
        [],
        snapshot,
        portfolio_df,
    )

    alert = next(
        item
        for item in items
        if item["title"] == "Stale portfolio prices"
    )

    assert alert["priority"] == "medium"
    assert alert["details"] == [
        "NVDA (12 days)"
    ]
