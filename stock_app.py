import streamlit as st
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
st.sidebar.header("Dashboard Controls")

ticker = st.sidebar.text_input(
    "Primary Stock Ticker",
    value=DEFAULT_PRIMARY_TICKER,
    key="primary_ticker_input"
).upper().strip()

comparison_ticker = st.sidebar.text_input(
    "Comparison Stock Ticker",
    value=DEFAULT_COMPARISON_TICKER,
    key="comparison_ticker_input"
).upper().strip()

period_index = PERIOD_OPTIONS.index(DEFAULT_PERIOD)

period = st.sidebar.selectbox(
    "Select Time Period",
    options=PERIOD_OPTIONS,
    index=period_index,
    key="period_selector"
)

show_company_overview = st.sidebar.checkbox(
    "Show Company Overview",
    value=True,
    key="show_company_overview"
)

show_recent_data = st.sidebar.checkbox(
    "Show Recent Data Table",
    value=True,
    key="show_recent_data"
)

if st.sidebar.button(
    "Refresh Market Data",
    key="refresh_market_data"
):
    clear_market_data_cache()
    st.sidebar.success("Market data cache cleared.")
    st.rerun()

primary_is_valid, primary_result = validate_ticker(ticker)

if not primary_is_valid:
    st.error(primary_result)
    st.stop()

ticker = primary_result

render_watchlist_sidebar(ticker)
render_market_cache_panel()
st.sidebar.caption(BUILD_LABEL)
render_release_notes_panel()

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

st.divider()

try:
    cache_only_mode = st.checkbox(
        "Use cached data only",
        value=True,
        help="Prevents Alpha Vantage API calls and only reads from Neon cache.",
    )

    render_developer_status_panel(cache_only_mode)

    show_diagnostics_page = st.sidebar.checkbox(
        "Show Diagnostics Page",
        value=False,
        help="Display app health, runtime, cache, and database diagnostics.",
    )

    if show_diagnostics_page:
        render_app_diagnostics_page(cache_only_mode)
        st.stop()

    refresh_market_data = st.button(
        "Refresh Market Data",
        help="Uses one Alpha Vantage API request and updates the Neon cache.",
        disabled=cache_only_mode,
    )

    stock_result = load_stock_dashboard_data(
        ticker,
        period,
        force_refresh=refresh_market_data,
        cache_only=cache_only_mode,
    )

    info = stock_result.info
    history = stock_result.history
    error_message = stock_result.error_message
    price_change = stock_result.price_change
    price_change_pct = stock_result.price_change_pct

    if refresh_market_data and error_message is None:
        clear_market_data_cache()
        st.success("Market data refreshed and saved to Neon.")

    if cache_only_mode:
        st.info("Data source: Neon cache only.")
    elif refresh_market_data:
        st.info("Data source: Alpha Vantage refresh.")
    else:
        st.info("Data source: Neon cache when available.")

    render_selected_ticker_freshness(ticker)

    if error_message:
        safe_error_message = get_user_safe_market_data_error(
            error_message,
            stock_result.is_quota_error,
        )
        log_warning(f"Market data load issue for {ticker}: {error_message}")

        if stock_result.is_quota_error:
            st.warning(safe_error_message)
            st.info(
                "This ticker is not cached in Neon yet. "
                "Try a ticker already saved in market_data_cache, "
                "or refresh again tomorrow when the API quota resets."
            )
            st.stop()

        st.error(safe_error_message)
        st.stop()

    if history is None or history.empty:
        st.error("No price history is available for " + ticker + ".")
        st.stop()

    history, volatility = add_technical_indicators(history)

    current_price, price_change_pct = calculate_price_change(history)

    if current_price is None:
        st.error("Not enough price data to analyze " + ticker + ".")
        st.stop()

    render_stock_header(
        info,
        ticker,
        current_price,
        price_change_pct,
        history,
    )

    render_company_profile(
        info,
        show_company_overview
    )

    render_technical_indicators(
        history,
        volatility
    )

    if comparison_ticker:
        comparison_is_valid, comparison_result = validate_ticker(
            comparison_ticker
        )

        if not comparison_is_valid:
            st.warning(comparison_result)
        else:
            comparison_ticker = comparison_result

            comparison_info, comparison_history, comparison_error = (
                load_stock_data(comparison_ticker, period)
            )

            if comparison_error:
                st.warning(comparison_error)
            elif comparison_history is None or comparison_history.empty:
                st.warning(
                    "No comparison data is available for "
                    + comparison_ticker
                    + "."
                )
            else:
                render_comparison_chart(
                    history,
                    comparison_history,
                    ticker,
                    comparison_ticker
                )

    render_price_chart(history, ticker)

    render_risk_dashboard(history, ticker)

except Exception as error:
    st.error("Unexpected app error: " + str(error))

    with open("app.log", "a", encoding="utf-8") as log_file:
        log_file.write("Unexpected app error: " + str(error) + "\n")
