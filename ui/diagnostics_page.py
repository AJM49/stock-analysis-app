from __future__ import annotations

import os
import platform
import sys

import streamlit as st

from app_metadata import APP_NAME, APP_VERSION, BUILD_LABEL, SPRINT_LABEL
from database import get_market_data_cache_summary
from database import get_portfolio_positions
from market_data import is_market_data_quota_limited


def get_secret_status(secret_name: str) -> bool:
    try:
        value = st.secrets.get(secret_name)
    except Exception:
        value = None

    return bool(value)


def get_env_status(env_name: str) -> bool:
    return bool(os.getenv(env_name))


def render_app_diagnostics_page(cache_only_mode: bool):
    st.header("App Diagnostics")

    st.subheader("Build")
    st.write("App name:", APP_NAME)
    st.write("Build:", BUILD_LABEL)
    st.write("Version:", APP_VERSION)
    st.write("Sprint:", SPRINT_LABEL)

    st.subheader("Runtime")
    st.write("Python:", sys.version.split()[0])
    st.write("Platform:", platform.platform())

    st.subheader("Secrets and Environment")
    st.write("Database secret:", get_secret_status("DATABASE_URL"))
    st.write("Database env:", get_env_status("DATABASE_URL"))
    st.write("Alpha Vantage secret:", get_secret_status("ALPHA_VANTAGE_API_KEY"))

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

    if cache_summary:
        st.subheader("Cached Tickers")
        st.dataframe(cache_summary, use_container_width=True)
    else:
        st.info("No cached market data yet.")
