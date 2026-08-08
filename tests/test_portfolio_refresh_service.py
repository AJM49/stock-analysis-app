import pandas as pd

import services.portfolio_refresh_service as service


class Position:
    def __init__(self, ticker):
        self.ticker = ticker


def test_refresh_skips_fresh_positions(monkeypatch):
    positions = [
        Position("AAPL"),
        Position("NOW"),
    ]

    portfolio_df = pd.DataFrame(
        [
            {
                "Ticker": "AAPL",
                "Price Freshness": "Fresh",
            },
            {
                "Ticker": "NOW",
                "Price Freshness": "Stale",
            },
        ]
    )

    monkeypatch.setattr(
        service,
        "get_portfolio_positions",
        lambda: positions,
    )

    monkeypatch.setattr(
        service,
        "build_portfolio_dataframe",
        lambda positions: portfolio_df,
    )

    calls = []

    def fake_get_stock_data(
        ticker,
        force_refresh=False,
        cache_only=False,
    ):
        calls.append(ticker)

        return (
            pd.DataFrame(
                {
                    "Close": [100.0],
                }
            ),
            None,
        )

    monkeypatch.setattr(
        service,
        "get_stock_data",
        fake_get_stock_data,
    )

    result = service.refresh_portfolio_prices()

    assert calls == ["NOW"]
    assert result["attempted_count"] == 1
    assert result["refreshed_count"] == 1
    assert result["skipped_fresh_count"] == 1
    assert result["refreshed_tickers"] == ["NOW"]
    assert result["skipped_fresh_tickers"] == ["AAPL"]


def test_refresh_attempts_missing_positions(monkeypatch):
    positions = [
        Position("ADVB"),
    ]

    portfolio_df = pd.DataFrame(
        [
            {
                "Ticker": "ADVB",
                "Price Freshness": "Missing",
            }
        ]
    )

    monkeypatch.setattr(
        service,
        "get_portfolio_positions",
        lambda: positions,
    )

    monkeypatch.setattr(
        service,
        "build_portfolio_dataframe",
        lambda positions: portfolio_df,
    )

    monkeypatch.setattr(
        service,
        "get_stock_data",
        lambda *args, **kwargs: (
            pd.DataFrame(
                {
                    "Close": [50.0],
                }
            ),
            None,
        ),
    )

    result = service.refresh_portfolio_prices()

    assert result["attempted_tickers"] == [
        "ADVB"
    ]

    assert result["refreshed_tickers"] == [
        "ADVB"
    ]


def test_refresh_records_provider_failure(monkeypatch):
    positions = [
        Position("HL"),
    ]

    portfolio_df = pd.DataFrame(
        [
            {
                "Ticker": "HL",
                "Price Freshness": "Stale",
            }
        ]
    )

    monkeypatch.setattr(
        service,
        "get_portfolio_positions",
        lambda: positions,
    )

    monkeypatch.setattr(
        service,
        "build_portfolio_dataframe",
        lambda positions: portfolio_df,
    )

    monkeypatch.setattr(
        service,
        "get_stock_data",
        lambda *args, **kwargs: (
            pd.DataFrame(),
            "Provider request failed",
        ),
    )

    result = service.refresh_portfolio_prices()

    assert result["attempted_count"] == 1
    assert result["refreshed_count"] == 0
    assert result["failed_tickers"] == [
        "HL"
    ]
