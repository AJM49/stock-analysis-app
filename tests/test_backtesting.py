from __future__ import annotations

import pandas as pd

from backtesting.engine import BacktestEngine
from strategies.moving_average import MovingAverageCrossoverStrategy


def build_sample_price_data() -> pd.DataFrame:
    """Create simple standardized test price data."""
    return pd.DataFrame(
        {
            "Date": pd.date_range("2026-01-01", periods=80, freq="D"),
            "Open": [100 + i for i in range(80)],
            "High": [101 + i for i in range(80)],
            "Low": [99 + i for i in range(80)],
            "Close": [100 + i for i in range(80)],
            "Volume": [1_000_000 for _ in range(80)],
        }
    )


def test_backtest_engine_returns_expected_keys() -> None:
    price_data = build_sample_price_data()
    strategy = MovingAverageCrossoverStrategy(short_window=5, long_window=20)
    engine = BacktestEngine(
        strategy=strategy,
        ticker="AAPL",
        starting_cash=10_000,
    )

    result = engine.run(price_data)

    expected_keys = {
        "ticker",
        "strategy_name",
        "starting_cash",
        "ending_value",
        "total_return_pct",
        "max_drawdown_pct",
        "number_of_trades",
        "equity_curve",
        "trades",
        "signals",
    }

    assert expected_keys.issubset(result.keys())
    assert result["ticker"] == "AAPL"
    assert result["starting_cash"] == 10_000
    assert not result["equity_curve"].empty
    assert not result["signals"].empty


def test_backtest_engine_rejects_empty_data() -> None:
    strategy = MovingAverageCrossoverStrategy(short_window=5, long_window=20)
    engine = BacktestEngine(strategy=strategy, ticker="AAPL")

    empty_data = pd.DataFrame(
        columns=["Date", "Open", "High", "Low", "Close", "Volume"]
    )

    try:
        engine.run(empty_data)
    except ValueError as error:
        assert "price_data cannot be empty" in str(error)
    else:
        raise AssertionError("Expected ValueError for empty price data")
