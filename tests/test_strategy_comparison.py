from __future__ import annotations

import pandas as pd

from backtesting.comparison import compare_strategies
from strategies.buy_and_hold import BuyAndHoldStrategy
from strategies.moving_average import MovingAverageCrossoverStrategy
from strategies.strategy_registry import build_strategy, get_available_strategies


def build_sample_price_data() -> pd.DataFrame:
    """Create simple standardized test price data."""
    return pd.DataFrame(
        {
            "Date": pd.date_range("2026-01-01", periods=100, freq="D"),
            "Open": [100 + i for i in range(100)],
            "High": [101 + i for i in range(100)],
            "Low": [99 + i for i in range(100)],
            "Close": [100 + i for i in range(100)],
            "Volume": [1_000_000 for _ in range(100)],
        }
    )


def test_buy_and_hold_generates_initial_buy_signal() -> None:
    price_data = build_sample_price_data()
    strategy = BuyAndHoldStrategy()

    signals = strategy.generate_signals(price_data)

    assert "signal" in signals.columns
    assert signals["signal"].iloc[0] == 1
    assert signals["signal"].iloc[1:].sum() == 0


def test_strategy_registry_returns_expected_strategies() -> None:
    strategies = get_available_strategies()

    assert "Buy and Hold" in strategies
    assert "Moving Average Crossover" in strategies


def test_strategy_registry_builds_strategy() -> None:
    strategy = build_strategy("Buy and Hold")

    assert isinstance(strategy, BuyAndHoldStrategy)


def test_compare_strategies_returns_summary() -> None:
    price_data = build_sample_price_data()

    strategies = [
        BuyAndHoldStrategy(),
        MovingAverageCrossoverStrategy(short_window=5, long_window=20),
    ]

    comparison = compare_strategies(
        price_data=price_data,
        ticker="AAPL",
        strategies=strategies,
        starting_cash=10_000,
    )

    assert comparison["ticker"] == "AAPL"
    assert not comparison["summary"].empty
    assert len(comparison["summary"]) == 2
    assert "best_return_strategy" in comparison
    assert "lowest_drawdown_strategy" in comparison
