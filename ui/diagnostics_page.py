from __future__ import annotations

import json
import os
import platform
import sys

import pandas as pd
import streamlit as st

from sqlalchemy import text

from app_metadata import APP_NAME, APP_VERSION, BUILD_LABEL, SPRINT_LABEL
from database import clear_market_data_cache_for_ticker
from database import delete_portfolio_position
from database import save_market_data_cache
from database import get_market_data_cache_summary
from database import get_portfolio_positions
from database import engine
from market_data import clear_market_data_cache
from market_data import clear_market_data_quota_limited
from market_data import validate_ticker
from market_data import set_market_data_quota_limited
from market_data import is_provider_quota_error
from market_data import fetch_alpha_vantage_daily_data
from market_data import is_market_data_quota_limited


def get_secret_status(secret_name: str) -> bool:
    try:
        value = st.secrets.get(secret_name)
    except Exception:
        value = None

    return bool(value)


def get_env_status(env_name: str) -> bool:
    return bool(os.getenv(env_name))



def portfolio_positions_to_rows(portfolio_positions):
    rows = []

    for position in portfolio_positions or []:
        rows.append(
            {
                "id": getattr(position, "id", ""),
                "ticker": getattr(position, "ticker", ""),
                "shares": getattr(position, "shares", 0),
                "average_cost": getattr(position, "average_cost", 0),
                "created_at": str(getattr(position, "created_at", "")),
                "updated_at": str(getattr(position, "updated_at", "")),
            }
        )

    return rows

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


def render_cache_admin_tools(admin_actions_enabled: bool):
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
        disabled=not admin_actions_enabled,
    ):
        success, message = clear_market_data_cache_for_ticker(selected_ticker)

        if success:
            clear_market_data_cache()
            st.success(message)
            st.rerun()

        st.error(message)


def render_portfolio_admin_tools(admin_actions_enabled: bool):
    st.subheader("Portfolio Positions")

    portfolio_positions = get_portfolio_positions()

    if not portfolio_positions:
        st.info("No portfolio positions yet.")
        return

    portfolio_rows = portfolio_positions_to_rows(portfolio_positions)
    portfolio_df = pd.DataFrame(portfolio_rows)
    st.dataframe(portfolio_df, use_container_width=True)

    selectable_rows = []

    for row in portfolio_rows:
        position_id = row.get("id")
        ticker = row.get("ticker", "")
        shares = row.get("shares", 0)
        average_cost = row.get("average_cost", 0)

        label = (
            str(position_id)
            + " | "
            + str(ticker)
            + " | "
            + str(shares)
            + " shares @ "
            + str(average_cost)
        )

        selectable_rows.append(
            {
                "label": label,
                "id": position_id,
            }
        )

    if not selectable_rows:
        return

    selected_label = st.selectbox(
        "Select portfolio position to delete",
        [item["label"] for item in selectable_rows],
        key="diagnostics_delete_portfolio_position_select",
    )

    selected_position_id = None

    for item in selectable_rows:
        if item["label"] == selected_label:
            selected_position_id = item["id"]
            break

    st.warning(
        "Deleting a portfolio position removes it from the database. "
        "This does not affect market data cache."
    )

    if st.button(
        "Delete Selected Portfolio Position",
        key="diagnostics_delete_selected_portfolio_position",
        disabled=not admin_actions_enabled,
    ):
        success, message = delete_portfolio_position(selected_position_id)

        if success:
            st.success(message)
            st.rerun()

        st.error(message)

def render_quota_admin_tools(admin_actions_enabled: bool):
    st.subheader("Provider Quota Admin")

    quota_locked = is_market_data_quota_limited()
    st.write("Provider quota locked:", quota_locked)

    if st.button(
        "Reset Provider Quota Lock",
        key="diagnostics_reset_provider_quota_lock",
        disabled=not admin_actions_enabled,
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



def render_seed_cache_admin_tools(admin_actions_enabled: bool):
    st.subheader("Seed Market Data Cache")

    st.write(
        "Use this only when Alpha Vantage quota is available. "
        "Seeding saves market history into Neon."
    )

    starter_ticker = st.selectbox(
        "Starter ticker",
        ["AAPL", "GOOGL", "CVNA", "DASH"],
        key="diagnostics_seed_starter_ticker",
    )

    custom_ticker = st.text_input(
        "Custom ticker",
        value="",
        key="diagnostics_seed_custom_ticker",
    )

    ticker_to_seed = custom_ticker.strip().upper() if custom_ticker else starter_ticker

    is_valid, ticker_result = validate_ticker(ticker_to_seed)

    if not is_valid:
        st.warning(ticker_result)
        return

    ticker_to_seed = ticker_result

    quota_locked = is_market_data_quota_limited()

    if quota_locked:
        st.warning(
            "Provider quota lock is active. Reset the quota lock only after quota resets."
        )

    if st.button(
        "Seed Selected Ticker",
        key="diagnostics_seed_selected_ticker",
        disabled=quota_locked or not admin_actions_enabled,
    ):
        history, error = fetch_alpha_vantage_daily_data(ticker_to_seed)

        if error:
            if is_provider_quota_error(error):
                set_market_data_quota_limited()
                st.error(error)
                st.warning("Provider quota lock enabled.")
                st.rerun()

            st.error(error)
            return

        if history is None or history.empty:
            st.warning("No market data returned for " + ticker_to_seed)
            return

        success, message = save_market_data_cache(ticker_to_seed, history)

        if success:
            clear_market_data_cache()
            clear_market_data_quota_limited()
            st.success(message)
            st.rerun()

        st.error(message)



def render_admin_action_guard() -> bool:
    st.subheader("Admin Safety Guard")

    st.warning(
        "Admin actions can modify cached market data or quota lock state. "
        "Enable this only when you intentionally want to make changes."
    )

    return st.checkbox(
        "Enable Admin Actions",
        value=False,
        key="diagnostics_enable_admin_actions",
    )



def build_diagnostics_report(cache_only_mode: bool) -> dict:
    cache_summary = get_market_data_cache_summary()
    portfolio_positions = get_portfolio_positions()

    cached_ticker_count = len(cache_summary) if cache_summary else 0
    portfolio_position_count = (
        len(portfolio_positions) if portfolio_positions else 0
    )

    return {
        "app_name": APP_NAME,
        "build": BUILD_LABEL,
        "version": APP_VERSION,
        "sprint": SPRINT_LABEL,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "database_secret": get_secret_status("DATABASE_URL"),
        "database_env": get_env_status("DATABASE_URL"),
        "alpha_vantage_secret": get_secret_status("ALPHA_VANTAGE_API_KEY"),
        "cache_only_mode": cache_only_mode,
        "provider_quota_locked": is_market_data_quota_limited(),
        "cached_ticker_count": cached_ticker_count,
        "portfolio_position_count": portfolio_position_count,
    }



def get_database_migration_status():
    required_tables = [
        "market_data_cache",
        "portfolio_positions",
        "watchlist_stocks",
    ]

    required_columns = {
        "market_data_cache": [
            "id",
            "ticker",
            "price_date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "fetched_at",
            "created_at",
            "updated_at",
        ],
        "portfolio_positions": [
            "id",
            "ticker",
            "shares",
            "buy_price",
            "created_at",
        ],
        "watchlist_stocks": [
            "id",
            "ticker",
            "created_at",
        ],
    }

    rows = []

    with engine.connect() as connection:
        existing_tables_result = connection.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
        )

        existing_tables = {
            row.table_name for row in existing_tables_result
        }

        for table_name in required_tables:
            table_exists = table_name in existing_tables

            rows.append(
                {
                    "object": table_name,
                    "type": "table",
                    "required": True,
                    "exists": table_exists,
                }
            )

            if not table_exists:
                for column_name in required_columns.get(table_name, []):
                    rows.append(
                        {
                            "object": table_name + "." + column_name,
                            "type": "column",
                            "required": True,
                            "exists": False,
                        }
                    )

                continue

            columns_result = connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = :table_name
                    """
                ),
                {
                    "table_name": table_name,
                },
            )

            existing_columns = {
                row.column_name for row in columns_result
            }

            for column_name in required_columns.get(table_name, []):
                rows.append(
                    {
                        "object": table_name + "." + column_name,
                        "type": "column",
                        "required": True,
                        "exists": column_name in existing_columns,
                    }
                )

    return rows


def render_migration_status_panel():
    st.subheader("Migration Status")

    try:
        migration_rows = get_database_migration_status()
    except Exception as error:
        st.error("Could not load migration status: " + str(error))
        return

    migration_df = pd.DataFrame(migration_rows)

    st.dataframe(migration_df, use_container_width=True)

    missing_items = [
        row for row in migration_rows if not row["exists"]
    ]

    if missing_items:
        st.warning(
            "Database migration is incomplete. Run: "
            "python3 scripts/run_database_migrations.py"
        )
        return

    st.success("Database migration status is healthy.")


def render_database_export_tools(cache_only_mode: bool):
    st.subheader("Database Export Tools")

    cache_summary = get_market_data_cache_summary()
    portfolio_positions = get_portfolio_positions()

    if cache_summary:
        cache_df = pd.DataFrame(cache_summary)
    else:
        cache_df = pd.DataFrame(
            columns=[
                "ticker",
                "row_count",
                "oldest_date",
                "newest_date",
                "last_fetched",
            ]
        )

    portfolio_rows = portfolio_positions_to_rows(portfolio_positions)
    portfolio_df = pd.DataFrame(portfolio_rows)

    diagnostics_report = build_diagnostics_report(cache_only_mode)

    st.download_button(
        "Export Cached Ticker Summary CSV",
        data=cache_df.to_csv(index=False),
        file_name="market_data_cache_summary.csv",
        mime="text/csv",
        key="export_cache_summary_csv",
    )

    st.download_button(
        "Export Portfolio Positions CSV",
        data=portfolio_df.to_csv(index=False),
        file_name="portfolio_positions.csv",
        mime="text/csv",
        key="export_portfolio_positions_csv",
    )

    st.download_button(
        "Export Diagnostics Report JSON",
        data=json.dumps(diagnostics_report, indent=2),
        file_name="diagnostics_report.json",
        mime="application/json",
        key="export_diagnostics_report_json",
    )


def render_database_admin_tools(cache_only_mode: bool):
    st.header("Database Admin Tools")

    admin_actions_enabled = render_admin_action_guard()

    render_table_count_summary()
    render_migration_status_panel()
    render_database_export_tools(cache_only_mode)
    render_seed_cache_admin_tools(admin_actions_enabled)
    render_cache_admin_tools(admin_actions_enabled)
    render_portfolio_admin_tools(admin_actions_enabled)
    render_quota_admin_tools(admin_actions_enabled)

def render_app_diagnostics_page(cache_only_mode: bool):
    st.header("App Diagnostics")

    render_build_diagnostics()
    render_runtime_diagnostics()
    render_secret_diagnostics()
    render_application_state(cache_only_mode)

    st.divider()

    render_database_admin_tools(cache_only_mode)
