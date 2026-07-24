from __future__ import annotations

import pandas as pd

from strategies.base_strategy import BaseStrategy


class MovingAverageCrossoverStrategy(BaseStrategy):
    """Moving-average crossover trading strategy."""

    name = "Moving Average Crossover"

    def __init__(self, short_window: int = 20, long_window: int = 50):
        if short_window <= 0:
            raise ValueError("short_window must be greater than 0")

        if long_window <= 0:
            raise ValueError("long_window must be greater than 0")

        if short_window >= long_window:
            raise ValueError("short_window must be less than long_window")

        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """Generate buy/sell signals from moving-average crossover logic."""
        required_columns = {"Date", "Open", "High", "Low", "Close", "Volume"}
        missing_columns = required_columns - set(price_data.columns)

        if missing_columns:
            raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

        signals = price_data.copy()

        signals["short_ma"] = (
            signals["Close"]
            .rolling(window=self.short_window, min_periods=1)
            .mean()
        )

        signals["long_ma"] = (
            signals["Close"]
            .rolling(window=self.long_window, min_periods=1)
            .mean()
        )

        signals["signal"] = 0

        previous_short = signals["short_ma"].shift(1)
        previous_long = signals["long_ma"].shift(1)

        buy_condition = (
            (signals["short_ma"] > signals["long_ma"])
            & (previous_short <= previous_long)
        )

        sell_condition = (
            (signals["short_ma"] < signals["long_ma"])
            & (previous_short >= previous_long)
        )

        signals.loc[buy_condition, "signal"] = 1
        signals.loc[sell_condition, "signal"] = -1

        return signals
