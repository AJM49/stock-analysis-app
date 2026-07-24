from __future__ import annotations

import pandas as pd

from strategies.base_strategy import BaseStrategy


class BuyAndHoldStrategy(BaseStrategy):
    """Buy once at the beginning and hold through the full period."""

    name = "Buy and Hold"

    def generate_signals(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """Generate one buy signal at the first valid row."""
        required_columns = {"Date", "Open", "High", "Low", "Close", "Volume"}
        missing_columns = required_columns - set(price_data.columns)

        if missing_columns:
            raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

        if price_data.empty:
            raise ValueError("price_data cannot be empty")

        signals = price_data.copy()
        signals["signal"] = 0

        first_index = signals.index[0]
        signals.loc[first_index, "signal"] = 1

        return signals
