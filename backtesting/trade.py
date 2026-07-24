from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Trade:
    """Represents one simulated trade."""

    date: datetime
    ticker: str
    action: str
    shares: float
    price: float
    cash_after_trade: float
    position_after_trade: float
