from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from market_data import calculate_price_change
from market_data import is_provider_quota_error
from market_data import load_stock_data
from market_data import set_market_data_quota_limited
from market_data import validate_ticker


@dataclass
class StockLoadResult:
    ticker: str
    period: str
    info: dict[str, Any]
    history: pd.DataFrame
    error_message: str | None
    is_quota_error: bool
    price_change: float
    price_change_pct: float


def validate_stock_ticker(ticker: str) -> tuple[bool, str]:
    return validate_ticker(ticker)


def load_stock_dashboard_data(
    ticker: str,
    period: str,
    force_refresh: bool = False,
) -> StockLoadResult:
    info, history, error_message = load_stock_data(
        ticker,
        period,
        force_refresh=force_refresh,
    )

    is_quota_error = is_provider_quota_error(error_message)

    if is_quota_error:
        set_market_data_quota_limited()

    price_change = 0.0
    price_change_pct = 0.0

    if error_message is None and history is not None and not history.empty:
        price_change, price_change_pct = calculate_price_change(history)

    return StockLoadResult(
        ticker=ticker,
        period=period,
        info=info,
        history=history,
        error_message=error_message,
        is_quota_error=is_quota_error,
        price_change=price_change,
        price_change_pct=price_change_pct,
    )


def should_stop_for_error(result: StockLoadResult) -> bool:
    return result.error_message is not None
