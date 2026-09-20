from __future__ import annotations

import pandas as pd
import pytest

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
        "completed_trades",
        "win_rate_pct",
        "average_gain",
        "average_loss",
        "best_trade",
        "worst_trade",
        "exposure_pct",
        "benchmark_name",
        "benchmark_ending_value",
        "benchmark_total_return_pct",
        "benchmark_max_drawdown_pct",
        "strategy_excess_return_pct",
        "annualized_return_pct",
        "annualized_volatility_pct",
        "sharpe_ratio",
        "sortino_ratio",
        "risk_max_drawdown_pct",
        "drawdown_duration",
        "value_at_risk_95_pct",
        "conditional_value_at_risk_95_pct",
        "calmar_ratio",
        "benchmark_equity_curve",
        "equity_curve",
        "trades",
        "completed_trade_details",
        "signals",
    }

    assert expected_keys.issubset(result.keys())
    assert result["ticker"] == "AAPL"
    assert result["starting_cash"] == 10_000
    assert not result["equity_curve"].empty
    assert not result["benchmark_equity_curve"].empty
    assert not result["signals"].empty
    assert result["benchmark_name"] == "Buy and Hold"
    assert isinstance(result["annualized_return_pct"], float)
    assert isinstance(result["annualized_volatility_pct"], float)
    assert isinstance(result["sharpe_ratio"], float)
    assert isinstance(result["sortino_ratio"], float)
    assert isinstance(result["risk_max_drawdown_pct"], float)
    assert isinstance(result["drawdown_duration"], int)
    assert isinstance(result["value_at_risk_95_pct"], float)
    assert isinstance(result["conditional_value_at_risk_95_pct"], float)
    assert isinstance(result["calmar_ratio"], float)


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


class RepeatedBuyStrategy:
    """Generate two buys followed by one full-position sell."""

    name = "Repeated Buy Test Strategy"

    def generate_signals(self, price_data: pd.DataFrame) -> pd.DataFrame:
        signals = price_data.copy()
        signals["signal"] = [1, 1, -1]
        return signals


def test_backtest_engine_uses_weighted_cost_basis_for_repeated_buys() -> None:
    price_data = pd.DataFrame(
        {
            "Date": pd.date_range("2026-01-01", periods=3, freq="D"),
            "Open": [100.0, 120.0, 130.0],
            "High": [101.0, 121.0, 131.0],
            "Low": [99.0, 119.0, 129.0],
            "Close": [100.0, 120.0, 130.0],
            "Volume": [1_000_000, 1_000_000, 1_000_000],
        }
    )

    engine = BacktestEngine(
        strategy=RepeatedBuyStrategy(),
        ticker="AAPL",
        starting_cash=1_000.0,
        trade_size_pct=0.5,
    )

    result = engine.run(price_data)

    completed = result["completed_trade_details"]

    assert len(completed) == 1

    # First buy: $500 / $100 = 5 shares.
    # Second buy: $250 / $120 = 2.083333 shares.
    # Total cost basis = $750 across 7.083333 shares.
    expected_shares = 5.0 + (250.0 / 120.0)
    expected_cost_basis = 750.0 / expected_shares
    expected_pnl = (130.0 * expected_shares) - 750.0
    expected_pnl_pct = (
        (130.0 - expected_cost_basis) / expected_cost_basis
    ) * 100

    assert completed.iloc[0]["shares"] == pytest.approx(expected_shares)
    assert completed.iloc[0]["entry_price"] == pytest.approx(
        expected_cost_basis
    )
    assert completed.iloc[0]["exit_price"] == pytest.approx(130.0)
    assert completed.iloc[0]["pnl"] == pytest.approx(expected_pnl)
    assert completed.iloc[0]["pnl_pct"] == pytest.approx(expected_pnl_pct)

    assert result["ending_value"] == pytest.approx(
        1_000.0 + expected_pnl
    )


class SingleTradeStrategy:
    """Generate one buy followed by one full-position sell."""

    name = "Single Trade Test Strategy"

    def generate_signals(self, price_data: pd.DataFrame) -> pd.DataFrame:
        signals = price_data.copy()
        signals["signal"] = [1, 0, -1]
        return signals


def test_backtest_engine_preserves_single_entry_trade_accounting() -> None:
    price_data = pd.DataFrame(
        {
            "Date": pd.date_range("2026-01-01", periods=3, freq="D"),
            "Open": [100.0, 110.0, 120.0],
            "High": [101.0, 111.0, 121.0],
            "Low": [99.0, 109.0, 119.0],
            "Close": [100.0, 110.0, 120.0],
            "Volume": [1_000_000, 1_000_000, 1_000_000],
        }
    )

    engine = BacktestEngine(
        strategy=SingleTradeStrategy(),
        ticker="AAPL",
        starting_cash=1_000.0,
        trade_size_pct=1.0,
    )

    result = engine.run(price_data)

    completed = result["completed_trade_details"]

    assert len(completed) == 1
    assert completed.iloc[0]["entry_price"] == pytest.approx(100.0)
    assert completed.iloc[0]["exit_price"] == pytest.approx(120.0)
    assert completed.iloc[0]["shares"] == pytest.approx(10.0)
    assert completed.iloc[0]["pnl"] == pytest.approx(200.0)
    assert completed.iloc[0]["pnl_pct"] == pytest.approx(20.0)

    assert result["starting_cash"] == pytest.approx(1_000.0)
    assert result["ending_value"] == pytest.approx(1_200.0)
    assert result["total_return_pct"] == pytest.approx(20.0)
    assert result["completed_trades"] == 1
    assert result["win_rate_pct"] == pytest.approx(100.0)
