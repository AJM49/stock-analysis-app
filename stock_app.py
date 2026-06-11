import streamlit as st

from config import APP_CAPTION
from config import APP_LAYOUT
from config import APP_PAGE_TITLE
from config import APP_TITLE
from config import DEFAULT_COMPARISON_TICKER
from config import DEFAULT_PERIOD
from config import DEFAULT_PRIMARY_TICKER
from config import PERIOD_OPTIONS
from database import get_database_status
from database import init_database
from indicators import add_technical_indicators
from market_data import calculate_price_change
from market_data import clear_market_data_cache
from market_data import load_stock_data
from market_data import validate_ticker
from portfolio import build_portfolio_dataframe
from ui_components import render_company_profile
from ui_components import render_portfolio_dashboard
from ui_components import render_portfolio_sidebar
from ui_components import render_stock_comparison
from ui_components import render_stock_export
from ui_components import render_stock_header
from ui_components import render_technical_indicators
from ui_components import render_watchlist_sidebar


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

portfolio_positions = render_portfolio_sidebar()
portfolio_df = build_portfolio_dataframe(portfolio_positions)

render_portfolio_dashboard(portfolio_df)

st.divider()

try:
    refresh_market_data = st.button(
        "Refresh Market Data",
        help="Uses one Alpha Vantage API request and updates the Neon cache."
    )

    info, history, error_message = load_stock_data(
        ticker,
        period,
        force_refresh=refresh_market_data
    )

    if refresh_market_data and error_message is None:
        clear_market_data_cache()
        st.success("Market data refreshed and saved to Neon.")

    if refresh_market_data:
        st.info("Data source: Alpha Vantage refresh.")
    else:
        st.info("Data source: Neon cache when available.")

    if error_message:
        st.error(error_message)
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
        price_change_pct
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
