import streamlit as st

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
    page_title="Stock Analysis Dashboard",
    layout="wide"
)

init_database()

st.title("Stock Analysis Dashboard")
st.caption("Sprint 10: App Hardening")

st.sidebar.header("Dashboard Controls")

ticker = st.sidebar.text_input(
    "Primary Stock Ticker",
    value="AAPL",
    key="primary_ticker_input"
).upper().strip()

comparison_ticker = st.sidebar.text_input(
    "Comparison Stock Ticker",
    value="MSFT",
    key="comparison_ticker_input"
).upper().strip()

period = st.sidebar.selectbox(
    "Select Time Period",
    options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
    index=2,
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
    info, history, error_message = load_stock_data(ticker, period)

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
                    "No comparison data found for "
                    + comparison_ticker
                    + "."
                )
            else:
                comp_price, comp_change_pct = calculate_price_change(
                    comparison_history
                )

                if comp_price is None:
                    st.warning(
                        "Not enough comparison data for "
                        + comparison_ticker
                        + "."
                    )
                else:
                    render_stock_comparison(
                        ticker,
                        comparison_ticker,
                        history,
                        comparison_history,
                        info,
                        comparison_info,
                        current_price,
                        price_change_pct,
                        comp_price,
                        comp_change_pct
                    )

    render_stock_export(
        history,
        ticker,
        period,
        show_recent_data
    )

except Exception as error:
    st.error(
        "The app hit an unexpected issue. Check app.log for details."
    )

    with open("app.log", "a", encoding="utf-8") as log_file:
        log_file.write("Unexpected app error: " + str(error) + "\n")
