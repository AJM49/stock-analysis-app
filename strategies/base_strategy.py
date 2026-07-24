from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseStrategy(ABC):
    """Base class for all trading strategies."""

    name: str = "Base Strategy"

    @abstractmethod
    def generate_signals(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals from standardized price data.

        Expected input columns:
        - Date
        - Open
        - High
        - Low
        - Close
        - Volume

        Expected output columns:
        - Date
        - Open
        - High
        - Low
        - Close
        - Volume
        - signal

        Signal meanings:
        1 = buy
        0 = hold
        -1 = sell
        """
        raise NotImplementedError
