"""Read-only adapter from cached company profiles to the valuation engine."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from database import get_cached_company_profile
from valuation.engine import ValuationInputs, ValuationResult, calculate_valuation


@dataclass(frozen=True)
class CachedValuationResult:
    ticker: str
    valuation: ValuationResult | None
    profile_source: str | None
    profile_fetched_at: datetime | None
    warnings: tuple[str, ...]


def calculate_cached_valuation(
    ticker: str,
    price: float,
    *,
    max_profile_age: timedelta = timedelta(days=7),
    now: datetime | None = None,
) -> CachedValuationResult:
    """Calculate available ratios from cached fundamentals and a supplied price.

    The caller owns price retrieval and its freshness policy. No network calls,
    writes, financial estimates, or scores occur in this adapter.
    """
    clean_ticker = ticker.strip().upper() if isinstance(ticker, str) else ""
    if not clean_ticker:
        raise ValueError("ticker must be a non-empty string")
    if max_profile_age <= timedelta(0):
        raise ValueError("max_profile_age must be positive")

    # Validate price even when no profile is available.
    calculate_valuation(ValuationInputs(ticker=clean_ticker, price=price))

    row = get_cached_company_profile(clean_ticker)
    if row is None:
        return CachedValuationResult(
            clean_ticker, None, None, None,
            ("Company profile unavailable in cache.",),
        )

    fetched_at = row.fetched_at
    if fetched_at is None:
        return CachedValuationResult(
            clean_ticker, None, row.source, None,
            ("Company profile freshness timestamp is missing.",),
        )

    reference_time = now if now is not None else datetime.now(UTC)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=UTC)
    fetched_utc = fetched_at.replace(tzinfo=UTC) if fetched_at.tzinfo is None else fetched_at.astimezone(UTC)
    reference_utc = reference_time.astimezone(UTC)
    if fetched_utc > reference_utc:
        return CachedValuationResult(
            clean_ticker, None, row.source, fetched_at,
            ("Company profile timestamp is in the future.",),
        )
    if reference_utc - fetched_utc > max_profile_age:
        return CachedValuationResult(
            clean_ticker, None, row.source, fetched_at,
            ("Company profile is stale; valuation was not calculated.",),
        )

    valuation = calculate_valuation(
        ValuationInputs(
            ticker=clean_ticker,
            price=price,
            earnings_per_share=row.eps,
            shares_outstanding=row.shares_outstanding,
            free_cash_flow=None,
        )
    )
    return CachedValuationResult(
        clean_ticker, valuation, row.source, fetched_at, valuation.warnings,
    )
