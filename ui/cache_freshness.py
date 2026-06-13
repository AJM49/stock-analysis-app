from __future__ import annotations

import streamlit as st

from database import get_market_data_freshness_for_ticker


def render_selected_ticker_freshness(ticker: str):
    freshness = get_market_data_freshness_for_ticker(ticker)

    if not freshness.get("has_cache"):
        st.info(freshness.get("message", "Ticker is not cached."))
        return

    newest_date = freshness.get("newest_date")
    age_days = freshness.get("age_days")

    if freshness.get("is_fresh"):
        st.success(
            "Cached data is fresh. "
            + "Newest cached date: "
            + str(newest_date)
        )
        return

    st.warning(
        "Cached data may be stale. "
        + "Newest cached date: "
        + str(newest_date)
        + " | Age: "
        + str(age_days)
        + " days"
    )
