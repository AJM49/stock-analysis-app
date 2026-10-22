"""Research-facing valuation display, separate from scoring logic."""
from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st

from valuation.integration import CachedValuationResult, calculate_cached_valuation


def _format_timestamp(timestamp: datetime | None) -> str:
    if timestamp is None:
        return "Unavailable"
    utc_timestamp = (
        timestamp.replace(tzinfo=UTC)
        if timestamp.tzinfo is None
        else timestamp.astimezone(UTC)
    )
    return utc_timestamp.strftime("%Y-%m-%d %H:%M UTC")


def _format_pe(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}x"


def _format_fcf_yield(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.2f}%"


def render_valuation_result(result: CachedValuationResult) -> None:
    """Show computed ratios and explicit limitations; never infer missing values."""
    st.subheader("Valuation Research")
    st.caption("Descriptive ratios only. No investment score or recommendation.")

    pe = result.valuation.pe_ratio if result.valuation else None
    fcf_yield = result.valuation.free_cash_flow_yield if result.valuation else None
    left, right = st.columns(2)
    left.metric("Calculated trailing P/E", _format_pe(pe))
    right.metric("Free cash flow yield", _format_fcf_yield(fcf_yield))

    st.caption(f"Fundamentals source: {result.profile_source or 'Unavailable'}")
    st.caption(f"Profile cache fetched: {_format_timestamp(result.profile_fetched_at)}")
    st.caption(
        "Price input: latest available daily close from the selected history. "
        "Not a real-time quote. Price observation date and provider freshness "
        "are not validated by this panel."
    )
    st.caption(
        "Profile cache age is checked against a seven-day limit. "
        "This does not establish the reporting period or recency of EPS."
    )
    for warning in result.warnings:
        st.warning(warning)


def render_cached_valuation_research(ticker: str, price: float) -> None:
    """Read the cached profile and display available valuation metrics."""
    try:
        result = calculate_cached_valuation(ticker, price)
    except (ValueError, ArithmeticError) as error:
        st.subheader("Valuation Research")
        st.warning(f"Valuation unavailable: {error}")
        return
    except Exception:
        st.subheader("Valuation Research")
        st.warning("Valuation unavailable: profile lookup or calculation failed.")
        return
    render_valuation_result(result)



def render_valuation_unavailable() -> None:
    """Show missing-price state without fetching fundamentals."""
    st.subheader("Valuation Research")
    st.caption("Descriptive ratios only. No investment score or recommendation.")

    left, right = st.columns(2)
    left.metric("Calculated trailing P/E", "N/A")
    right.metric("Free cash flow yield", "N/A")

    st.warning(
        "Valuation unavailable: a valid market price is required. "
        "No valuation calculation or fundamentals lookup was performed."
    )
