from __future__ import annotations

from typing import Any

import pandas as pd

from backtesting.metrics import calculate_max_drawdown, calculate_total_return


def run_buy_and_hold_benchmark(
    price_data: pd.DataFrame,
    starting_cash: float,
) -> dict[str, Any]:
    """Run a simple buy-and-hold benchmark on standardized price data."""
    required_columns = {"Date", "Close"}
    missing_columns = required_columns - set(price_data.columns)

    if missing_columns:
        raise ValueError(f"Missing required benchmark columns: {sorted(missing_columns)}")

    if price_data.empty:
        raise ValueError("price_data cannot be empty")

    if starting_cash <= 0:
        raise ValueError("starting_cash must be greater than 0")

    benchmark_data = price_data[["Date", "Close"]].copy()
    benchmark_data["Close"] = pd.to_numeric(
        benchmark_data["Close"],
        errors="coerce",
    )

    benchmark_data = benchmark_data.dropna(subset=["Close"])
    benchmark_data = benchmark_data[benchmark_data["Close"] > 0]

    if benchmark_data.empty:
        raise ValueError("benchmark_data cannot be empty after cleaning")

    first_close = float(benchmark_data["Close"].iloc[0])
    shares = starting_cash / first_close

    benchmark_data["benchmark_position_value"] = benchmark_data["Close"] * shares
    benchmark_data["benchmark_total_value"] = benchmark_data["benchmark_position_value"]

    ending_value = float(benchmark_data["benchmark_total_value"].iloc[-1])

    total_return_pct = calculate_total_return(
        starting_value=starting_cash,
        ending_value=ending_value,
    )

    max_drawdown_pct = calculate_max_drawdown(
        benchmark_data["benchmark_total_value"]
    )

    return {
        "benchmark_name": "Buy and Hold",
        "benchmark_starting_cash": float(starting_cash),
        "benchmark_start_price": first_close,
        "benchmark_shares": shares,
        "benchmark_ending_value": ending_value,
        "benchmark_total_return_pct": total_return_pct,
        "benchmark_max_drawdown_pct": max_drawdown_pct,
        "benchmark_equity_curve": benchmark_data,
    }
