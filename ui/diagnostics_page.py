from __future__ import annotations

import os
import platform
import sys

import pandas as pd
import streamlit as st

from app_metadata import APP_NAME, APP_VERSION, BUILD_LABEL, SPRINT_LABEL
from database import clear_market_data_cache_for_ticker
from database import get_market_data_cache_summary
from database import get_portfolio_positions
from market_data import clear_market_data_cache
from market_data import clear_market_data_quota_limited
from market_data import is_market_data_quota_limited


def get_secret_status(secret_name: str) -> bool:
    try:
        value = st.secrets.get(secret_name)
    except Exception:
        value = None

    return bool(value)


def get_env_status(env_name: str) -> bool:
    return bool(os.getenv(env_name))


def render_build_diagnostics():
    st.subheader("Build")
    st.write("App name:", APP_NAME)
    st.write("Build:", BUILD_LABEL)
    st.write("Version:", APP_VERSION)
    st.write("Sprint:", SPRINT_LABEL)


def render_runtime_diagnostics():
    st.subheader("Runtime")
    st.write("Python:", sys.version.split()[0])
    st.write("Platform:", platform.platform())


def render_secret_diagnostics():
    st.subheader("Secrets and Environment")
    st.write("Database secret:", get_secret_status("DATABASE_URL"))
    st.write("Database env:", get_env_status("DATABASE_URL"))
    st.write("Alpha Vantage secret:", get_secret_status("ALPHA_VANTAGE_API_KEY"))


def render_application_state(cache_only_mode: bool):
    st.subheader("Application State")

    cache_summary = get_market_data_cache_summary()
    portfolio_positions = get_portfolio_positions()

    cached_ticker_count = len(cache_summary) if cache_summary else 0
    portfolio_position_count = (
        len(portfolio_positions) if portfolio_positions else 0
    )

    st.write("Cache-only mode:", cache_only_mode)
    st.write("Provider quota locked:", is_market_data_quota_limited())
    st.write("Cached ticker count:", cached_ticker_count)
    st.write("Portfolio position count:", portfolio_position_count)


def render_cache_admin_tools():
    st.subheader("Market Data Cache Admin")

    cache_summary = get_market_data_cache_summary()

    if not cache_summary:
        st.info("No cached market data yet.")
        return

    cache_df = pd.DataFrame(cache_summary)
    st.dataframe(cache_df, use_container_width=True)

    cached_tickers = [item["ticker"] for item in cache_summary]

    selected_ticker = st.selectbox(
        "Select cached ticker",
        cached_tickers,
        key="diagnostics_cached_ticker_select",
    )

    st.warning(
        "Clearing a cached ticker removes its saved market history from Neon."
    )

    if st.button(
        "Clear Selected Cached Ticker",
        key="diagnostics_clear_selected_cached_ticker",
    ):
        success, message = clear_market_data_cache_for_ticker(selected_ticker)

        if success:
            clear_market_data_cache()
            st.success(message)
            st.rerun()

        st.error(message)


def render_portfolio_admin_tools():
    st.subheader("Portfolio Positions")

    portfolio_positions = get_portfolio_positions()

    if not portfolio_positions:
        st.info("No portfolio positions yet.")
        return

    portfolio_df = pd.DataFrame(portfolio_positions)
    st.dataframe(portfolio_df, use_container_width=True)


def render_quota_admin_tools():
    st.subheader("Provider Quota Admin")

    quota_locked = is_market_data_quota_limited()
    st.write("Provider quota locked:", quota_locked)

    if st.button(
        "Reset Provider Quota Lock",
        key="diagnostics_reset_provider_quota_lock",
    ):
        clear_market_data_quota_limited()
        st.success("Provider quota lock reset.")
        st.rerun()


def render_table_count_summary():
    st.subheader("Database Table Counts")

    cache_summary = get_market_data_cache_summary()
    portfolio_positions = get_portfolio_positions()

    cached_ticker_count = len(cache_summary) if cache_summary else 0
    portfolio_position_count = (
        len(portfolio_positions) if portfolio_positions else 0
    )

    counts = pd.DataFrame(
        [
            {
                "table": "market_data_cache",
                "count_type": "cached tickers",
                "count": cached_ticker_count,
            },
            {
                "table": "portfolio_positions",
                "count_type": "positions",
                "count": portfolio_position_count,
            },
        ]
    )

    st.dataframe(counts, use_container_width=True)


def render_database_admin_tools():
    st.header("Database Admin Tools")

    render_table_count_summary()
    render_cache_admin_tools()
    render_portfolio_admin_tools()
    render_quota_admin_tools()


def render_app_diagnostics_page(cache_only_mode: bool):
    st.header("App Diagnostics")

    render_build_diagnostics()
    render_runtime_diagnostics()
    render_secret_diagnostics()
    render_application_state(cache_only_mode)

    st.divider()

    render_database_admin_tools()
