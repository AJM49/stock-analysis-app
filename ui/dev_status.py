from __future__ import annotations

import os

import streamlit as st

from database import get_market_data_cache_summary
from database import get_portfolio_positions


def safe_count(items):
    if items is None:
        return 0

    try:
        return len(items)
    except TypeError:
        return 0


def render_developer_status_panel(cache_only_mode: bool):
    with st.sidebar.expander("Developer Status"):
        database_url_exists = bool(os.getenv("DATABASE_URL"))

        try:
            secret_database_url_exists = bool(st.secrets.get("DATABASE_URL"))
        except Exception:
            secret_database_url_exists = False

        try:
            alpha_vantage_key_exists = bool(
                st.secrets.get("ALPHA_VANTAGE_API_KEY")
            )
        except Exception:
            alpha_vantage_key_exists = False

        try:
            cache_summary = get_market_data_cache_summary()
            cached_ticker_count = safe_count(cache_summary)
            database_status = "Connected"
        except Exception:
            cached_ticker_count = 0
            database_status = "Unavailable"

        try:
            portfolio_positions = get_portfolio_positions()
            portfolio_position_count = safe_count(portfolio_positions)
        except Exception:
            portfolio_position_count = 0

        st.write("Database:", database_status)
        st.write("DATABASE_URL env:", database_url_exists)
        st.write("DATABASE_URL secret:", secret_database_url_exists)
        st.write("Alpha Vantage secret:", alpha_vantage_key_exists)
        st.write("Cache-only mode:", cache_only_mode)
        st.write("Cached tickers:", cached_ticker_count)
        st.write("Portfolio positions:", portfolio_position_count)
