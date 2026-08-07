import streamlit as st
from features.company_research import render_company_research
from controllers.stock_controller import load_stock_dashboard_data
from controllers.stock_controller import should_stop_for_error
from core.user_messages import get_user_safe_app_error
from core.user_messages import get_user_safe_market_data_error
from core.app_logging import log_error, log_warning

from config import APP_CAPTION
from config import APP_LAYOUT
from config import APP_PAGE_TITLE
from config import APP_TITLE
from config import DEFAULT_COMPARISON_TICKER
from config import DEFAULT_PERIOD
from config import DEFAULT_PRIMARY_TICKER
from config import PERIOD_OPTIONS
from database import get_database_status
from database import get_portfolio_positions
from database import get_portfolio_snapshots
from database import init_database
from indicators import add_technical_indicators
from market_data import calculate_price_change
from market_data import clear_market_data_cache
from market_data import load_stock_data
from market_data import validate_ticker
from controllers.portfolio_controller import build_portfolio_dashboard_data
from ui_components import render_company_profile
from ui.portfolio_views import render_portfolio_dashboard
from ui.portfolio_views import render_portfolio_snapshot_history
from ui.portfolio_views import render_portfolio_snapshot_export
from ui.portfolio_views import render_portfolio_value_history_chart
from ui.portfolio_views import render_portfolio_performance_summary_cards
from ui.portfolio_views import render_latest_snapshot_status_panel
from ui.portfolio_views import render_portfolio_report_summary
from ui.portfolio_views import render_portfolio_gain_loss_history_chart
from ui.portfolio_views import render_portfolio_risk_score_history_chart
from ui_components import render_portfolio_sidebar
from ui.sidebar import render_save_portfolio_snapshot_control
from ui.sidebar import render_portfolio_snapshot_cleanup_control
from ui_components import render_comparison_chart
from ui_components import render_stock_export
from ui_components import render_stock_header
from ui_components import render_technical_indicators
from ui_components import render_watchlist_sidebar
from ui_components import render_developer_status_panel
from ui_components import render_app_diagnostics_page
from ui_components import render_market_cache_panel
from ui_components import render_release_notes_panel
from ui_components import render_selected_ticker_freshness
from ui_components import render_price_chart
from ui_components import render_risk_dashboard
from app_metadata import APP_NAME, BUILD_LABEL, SPRINT_LABEL

st.set_page_config(
    page_title=APP_PAGE_TITLE,
    layout=APP_LAYOUT
)

init_database()

st.title(APP_TITLE)
st.caption(APP_CAPTION)

database_status = get_database_status()
st.sidebar.info("Database: " + database_status)
st.sidebar.header("Stock Analysis Platform")

active_section = st.sidebar.radio(
    "Navigation",
    options=[
        "Dashboard",
        "Company Research",
        "Watchlist",
        "Portfolio Summary",
        "Factor Research",
        "Backtesting",
        "Strategy Comparison",
        "Risk Analytics",
        "Portfolio Optimization",
        "Paper Trading",
        "Model Lab",
        "System Settings",
    ],
    index=0,
    key="main_navigation",
)

st.sidebar.divider()

if "selected_ticker" not in st.session_state:
    st.session_state["selected_ticker"] = DEFAULT_PRIMARY_TICKER

if "selected_comparison_ticker" not in st.session_state:
    st.session_state["selected_comparison_ticker"] = DEFAULT_COMPARISON_TICKER

if active_section == "Company Research":
    st.sidebar.subheader("Company Research Controls")

    ticker = st.sidebar.text_input(
        "Primary Stock Ticker",
        value=st.session_state["selected_ticker"],
        key="primary_ticker_input",
    ).upper().strip()

    comparison_ticker = st.sidebar.text_input(
        "Comparison Stock Ticker",
        value=st.session_state["selected_comparison_ticker"],
        key="comparison_ticker_input",
    ).upper().strip()

    st.session_state["selected_ticker"] = ticker
    st.session_state["selected_comparison_ticker"] = comparison_ticker

else:
    ticker = st.session_state["selected_ticker"]
    comparison_ticker = st.session_state["selected_comparison_ticker"]


period = DEFAULT_PERIOD
show_company_overview = True
show_recent_data = True

primary_is_valid, primary_result = validate_ticker(ticker)

if primary_is_valid:
    ticker = primary_result

if active_section == "Company Research":
    st.sidebar.subheader("Research Settings")

    period_index = PERIOD_OPTIONS.index(DEFAULT_PERIOD)

    period = st.sidebar.selectbox(
        "Select Time Period",
        options=PERIOD_OPTIONS,
        index=period_index,
        key="period_selector",
    )

    show_company_overview = st.sidebar.checkbox(
        "Show Company Overview",
        value=True,
        key="show_company_overview",
    )

    show_recent_data = st.sidebar.checkbox(
        "Show Recent Data Table",
        value=True,
        key="show_recent_data",
    )

    if st.sidebar.button(
        "Refresh Market Data",
        key="refresh_market_data",
    ):
        clear_market_data_cache()
        st.sidebar.success("Market data cache cleared.")
        st.rerun()

    if not primary_is_valid:
        st.sidebar.warning(primary_result)

elif active_section == "Watchlist":
    if primary_is_valid:
        render_watchlist_sidebar(ticker)
    else:
        st.sidebar.warning(primary_result)

render_market_cache_panel()
st.sidebar.caption(BUILD_LABEL)
render_release_notes_panel()



st.divider()
if active_section == "Dashboard":
    st.subheader("Dashboard")
    st.info("Dashboard overview will be assembled here.")

elif active_section == "Company Research":
    st.header("Company Research")

    if primary_is_valid:
        render_company_research(
            ticker,
            comparison_ticker,
            period,
            show_company_overview,
        )
    else:
        st.info("Enter a valid stock ticker to open Company Research.")

elif active_section == "Portfolio Summary":
    st.header("Portfolio Summary")

    render_portfolio_sidebar()
    st.sidebar.success("Sprint 62: Portfolio UX and Release Hardening")
    portfolio_positions = get_portfolio_positions()
    portfolio_df = build_portfolio_dashboard_data(portfolio_positions)


    render_save_portfolio_snapshot_control(portfolio_df)
    render_portfolio_snapshot_cleanup_control()
    render_portfolio_dashboard(portfolio_df)

    snapshot_limit_label = st.sidebar.selectbox(
        "Portfolio history records",
        options=[
            "25 snapshots",
            "50 snapshots",
            "100 snapshots",
            "250 snapshots",
            "All snapshots",
        ],
        index=2,
        key="portfolio_snapshot_limit_select",
    )

    snapshot_limit_map = {
        "25 snapshots": 25,
        "50 snapshots": 50,
        "100 snapshots": 100,
        "250 snapshots": 250,
        "All snapshots": 10000,
    }

    portfolio_snapshots = get_portfolio_snapshots(
        limit=snapshot_limit_map[snapshot_limit_label]
    )

    snapshot_risk_level_filter = st.sidebar.selectbox(
        "Portfolio snapshot risk level",
        options=[
            "All Risk Levels",
            "Low Risk",
            "Moderate Risk",
            "Elevated Risk",
            "High Risk",
            "No Data",
        ],
        index=0,
        key="portfolio_snapshot_risk_level_filter",
    )

    snapshot_risk_notes_search = st.sidebar.text_input(
        "Portfolio snapshot risk notes search",
        value="",
        key="portfolio_snapshot_risk_notes_search",
    )

    if snapshot_risk_level_filter != "All Risk Levels":
        portfolio_snapshots = [
            snapshot
            for snapshot in portfolio_snapshots
            if (getattr(snapshot, "risk_level", None) or "No Data")
            == snapshot_risk_level_filter
        ]

    if snapshot_risk_notes_search.strip():
        search_term = snapshot_risk_notes_search.strip().lower()

        portfolio_snapshots = [
            snapshot
            for snapshot in portfolio_snapshots
            if search_term
            in (
                str(getattr(snapshot, "risk_notes", "") or "")
                + " "
                + str(getattr(snapshot, "risk_level", "") or "")
                + " "
                + str(getattr(snapshot, "snapshot_date", "") or "")
            ).lower()
        ]

    snapshot_count = len(portfolio_snapshots) if portfolio_snapshots else 0

    render_latest_snapshot_status_panel(portfolio_df, portfolio_snapshots)

    with st.expander("Portfolio Report Center", expanded=False):
        st.caption(
            "Use the TXT export for copy-ready written updates. "
            "Use the CSV export for Excel, Google Sheets, dashboards, and structured reporting."
        )
        render_portfolio_report_summary(portfolio_df, portfolio_snapshots)

    st.header("Portfolio Performance History")
    st.caption(
        f"Showing {snapshot_count} saved portfolio snapshot(s). "
        f"Risk level filter: {snapshot_risk_level_filter}. "
        f"Risk notes search: {snapshot_risk_notes_search or 'None'}."
    )

    if snapshot_count == 0 and (
        snapshot_risk_level_filter != "All Risk Levels"
        or snapshot_risk_notes_search.strip()
    ):
        st.warning(
            "No portfolio snapshots match the current risk filters. "
            "Try searching for VTV, ETF, concentration, missing, price, "
            "Moderate Risk, or clear the filters."
        )

    with st.expander("View Portfolio Performance History", expanded=True):
        render_portfolio_performance_summary_cards(portfolio_snapshots)
        render_portfolio_value_history_chart(portfolio_snapshots)
        render_portfolio_gain_loss_history_chart(portfolio_snapshots)
        render_portfolio_risk_score_history_chart(portfolio_snapshots)
        render_portfolio_snapshot_export(portfolio_snapshots)
        render_portfolio_snapshot_history(portfolio_snapshots)

elif active_section == "Watchlist":
    st.subheader("Watchlist")
    st.info("Watchlist routing is next.")

else:
    st.subheader(active_section)
    st.info(f"{active_section} is planned for a future version.")
