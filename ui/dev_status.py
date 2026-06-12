from __future__ import annotations

import os

import streamlit as st

from app_metadata import APP_VERSION, BUILD_LABEL, SPRINT_LABEL
from database import get_market_data_cache_summary
from database import get_portfolio_positions


def get_secret_status(secret_name: str) -> bool:
    try:
        value = st.secrets.get(secret_name)
    except Exception:
        value = None

    return bool(value)


def get_env_status(env_name: str) -> bool:
    return bool(os.getenv(env_name))


def render_developer_status_panel(cache_only_mode: bool):
    with st.sidebar.expander("Developer Status"):
        database_secret_loaded = get_secret_status("DATABASE_URL")
        database_env_loaded = get_env_status("DATABASE_URL")
        alpha_vantage_secret_loaded = get_secret_status("ALPHA_VANTAGE_API_KEY")

        cache_summary = get_market_data_cache_summary()
        portfolio_positions = get_portfolio_positions()

        cached_ticker_count = len(cache_summary) if cache_summary else 0
        portfolio_position_count = (
            len(portfolio_positions) if portfolio_positions else 0
        )

        st.write("Build:", BUILD_LABEL)
        st.write("Version:", APP_VERSION)
        st.write("Sprint:", SPRINT_LABEL)
        st.write("Database secret:", database_secret_loaded)
        st.write("Database env:", database_env_loaded)
        st.write("Alpha Vantage secret:", alpha_vantage_secret_loaded)
        st.write("Cache-only mode:", cache_only_mode)
        st.write("Cached ticker count:", cached_ticker_count)
        st.write("Portfolio position count:", portfolio_position_count)
