from __future__ import annotations

import streamlit as st

from database import clear_market_data_cache_for_ticker
from database import get_market_data_cache_summary
from database import save_market_data_cache
from market_data import clear_market_data_cache
from market_data import clear_market_data_quota_limited
from market_data import fetch_alpha_vantage_daily_data
from market_data import is_market_data_quota_limited
from market_data import is_provider_quota_error
from market_data import set_market_data_quota_limited


def render_market_cache_panel():
    st.sidebar.divider()
    st.sidebar.header("Market Data Cache")

    cache_summary = get_market_data_cache_summary()

    if not cache_summary:
        st.sidebar.info("No cached market data yet.")
        return

    cached_tickers = [
        item["ticker"] for item in cache_summary
    ]

    selected_ticker = st.sidebar.selectbox(
        "Cached Tickers",
        cached_tickers,
        key="cached_ticker_select"
    )

    selected_summary = None

    for item in cache_summary:
        if item["ticker"] == selected_ticker:
            selected_summary = item
            break

    if selected_summary is None:
        return

    st.sidebar.write("Rows:", selected_summary["row_count"])
    st.sidebar.write("Oldest:", selected_summary["oldest_date"])
    st.sidebar.write("Newest:", selected_summary["newest_date"])
    st.sidebar.write("Fetched:", selected_summary["last_fetched"])

    quota_limited = is_market_data_quota_limited()

    if quota_limited:
        st.sidebar.warning(
            "Market data refresh is locked because the provider quota was reached."
        )

        if st.sidebar.button(
            "Reset Quota Lock",
            key="reset_market_quota_lock"
        ):
            clear_market_data_quota_limited()
            st.sidebar.success("Quota lock reset.")
            st.rerun()

    if st.sidebar.button(
        "Refresh Selected Cache",
        key="refresh_selected_market_cache",
        disabled=quota_limited
    ):
        history, error = fetch_alpha_vantage_daily_data(selected_ticker)

        if error:
            if is_provider_quota_error(error):
                set_market_data_quota_limited()
                st.sidebar.error(error)
                st.sidebar.warning("Refresh locked to protect your API quota.")
                st.rerun()

            st.sidebar.error(error)
            return

        if history is None or history.empty:
            st.sidebar.warning(
                "No market data returned for " + selected_ticker
            )
            return

        success, message = save_market_data_cache(
            selected_ticker,
            history
        )

        if success:
            clear_market_data_cache()
            clear_market_data_quota_limited()
            st.sidebar.success(message)
            st.rerun()

        st.sidebar.error(message)

    if st.sidebar.button(
        "Clear Selected Cache",
        key="clear_selected_market_cache"
    ):
        success, message = clear_market_data_cache_for_ticker(
            selected_ticker
        )

        if success:
            clear_market_data_cache()
            st.sidebar.success(message)
            st.rerun()

        st.sidebar.error(message)
