"""Pure, dependency-free valuation calculations.

Ratios are descriptive, not investment recommendations or valuation scores.
Free cash flow and share counts must refer to compatible periods and units.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class ValuationInputs:
    ticker: str
    price: float
    earnings_per_share: float | None = None
    free_cash_flow: float | None = None
    shares_outstanding: float | None = None


@dataclass(frozen=True)
class ValuationResult:
    ticker: str
    pe_ratio: float | None
    free_cash_flow_yield: float | None
    warnings: tuple[str, ...]


def _finite_number(name: str, value: float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    number = float(value)
    if not isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def calculate_valuation(inputs: ValuationInputs) -> ValuationResult:
    """Calculate trailing P/E and FCF yield as a decimal (0.05 means 5%).

    Missing inputs leave the affected ratio unavailable. Negative earnings
    produce no meaningful conventional P/E; negative free cash flow produces
    a valid negative yield. No provider calls or implicit data imputation.
    """
    ticker = inputs.ticker.strip().upper() if isinstance(inputs.ticker, str) else ""
    if not ticker:
        raise ValueError("ticker must be a non-empty string")

    price = _finite_number("price", inputs.price)
    if price is None or price <= 0:
        raise ValueError("price must be greater than zero")

    eps = _finite_number("earnings_per_share", inputs.earnings_per_share)
    fcf = _finite_number("free_cash_flow", inputs.free_cash_flow)
    shares = _finite_number("shares_outstanding", inputs.shares_outstanding)
    if shares is not None and shares <= 0:
        raise ValueError("shares_outstanding must be greater than zero")

    warnings: list[str] = []
    pe_ratio = None
    if eps is None:
        warnings.append("P/E unavailable: earnings per share is missing.")
    elif eps <= 0:
        warnings.append("P/E unavailable: earnings per share is zero or negative.")
    else:
        pe_ratio = price / eps

    fcf_yield = None
    if fcf is None:
        warnings.append("FCF yield unavailable: free cash flow is missing.")
    elif shares is None:
        warnings.append("FCF yield unavailable: shares outstanding is missing.")
    else:
        market_cap = price * shares
        if not isfinite(market_cap):
            raise ValueError("calculated market capitalization must be finite")
        fcf_yield = fcf / market_cap
        if not isfinite(fcf_yield):
            raise ValueError("calculated free cash flow yield must be finite")
        if fcf < 0:
            warnings.append("FCF yield is negative because free cash flow is negative.")

    return ValuationResult(ticker, pe_ratio, fcf_yield, tuple(warnings))
