cat > stock_app.py <<'PY'
import pandas as pd
import streamlit as st
import yfinance as yf

from database import add_to_watchlist
from database import get_watchlist
from database import init_database
from database import remove_from_watchlist


st.set_page_config(
    page_title="Stock Analysis Dashboard",
    layout="wide"
)

init_database()

st.title("Stock Analysis Dashboard")
st.caption("Sprint 4: SQLite Watchlist Foundation")

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


def load_stock_data(symbol, selected_period):
    stock = yf.Ticker(symbol)
    info = stock.info
    history = stock.history(period=selected_period)
    return info, history


def calculate_price_change(history):
    current_price = history["Close"].iloc[-1]
    previous_close = history["Close"].iloc[-2]
    price_change_pct = ((current_price - previous_close) / previous_close) 
* 100
    return current_price, price_change_pct


st.sidebar.divider()
st.sidebar.header("Saved Watchlist")

if st.sidebar.button(
    "Save Primary Ticker",
    key="save_primary_ticker"
):
    success, message = add_to_watchlist(ticker)

    if success:
        st.sidebar.success(message)
    else:
        st.sidebar.warning(message)

watchlist_items = get_watchlist()

if watchlist_items:
    selected_watchlist_ticker = st.sidebar.selectbox(
        "Saved Tickers",
        options=[stock.ticker for stock in watchlist_items],
        key="saved_tickers_select"
    )

    if st.sidebar.button(
        "Remove Selected Ticker",
        key="remove_selected_ticker"
    ):
        success, message = 
remove_from_watchlist(selected_watchlist_ticker)

        if success:
            st.sidebar.success(message)
            st.rerun()
        else:
            st.sidebar.warning(message)

else:
    st.sidebar.info("No saved tickers yet.")


if ticker:
    try:
        info, history = load_stock_data(ticker, period)

        if history.empty:
            st.error("Invalid primary ticker symbol.")
        else:
            history["MA20"] = history["Close"].rolling(window=20).mean()
            history["MA50"] = history["Close"].rolling(window=50).mean()

            current_price, price_change_pct = 
calculate_price_change(history)

            st.subheader(info.get("longName", ticker))

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Current Price",
                f"${current_price:.2f}",
                f"{price_change_pct:.2f}%"
            )

            col2.metric(
                "52 Week High",
                f"${info.get('fiftyTwoWeekHigh', 0):.2f}"
            )

            col3.metric(
                "52 Week Low",
                f"${info.get('fiftyTwoWeekLow', 0):.2f}"
            )

            col4, col5, col6 = st.columns(3)

            col4.metric(
                "Market Cap",
                f"${info.get('marketCap', 0):,}"
            )

            col5.metric(
                "Volume",
                f"{info.get('volume', 0):,}"
            )

            col6.metric(
                "Average Volume",
                f"{info.get('averageVolume', 0):,}"
            )

            pe_ratio = info.get("trailingPE")
            dividend_yield = info.get("dividendYield")
            beta = info.get("beta")

            col7, col8, col9 = st.columns(3)

            col7.metric(
                "P/E Ratio",
                f"{pe_ratio:.2f}" if pe_ratio else "N/A"
            )

            col8.metric(
                "Dividend Yield",
                f"{dividend_yield * 100:.2f}%" if dividend_yield else 
"N/A"
            )

            col9.metric(
                "Beta",
                f"{beta:.2f}" if beta else "N/A"
            )

            st.divider()

            st.subheader("Company Profile")
            st.write("Sector:", info.get("sector", "N/A"))
            st.write("Industry:", info.get("industry", "N/A"))

            if show_company_overview:
                st.subheader("Company Overview")
                st.write(
                    info.get(
                        "longBusinessSummary",
                        "No company description available."
                    )
                )

            st.divider()

            st.subheader("Price and Moving Averages")

            chart_data = history[["Close", "MA20", "MA50"]]
            st.line_chart(chart_data)

            st.divider()

            st.subheader("Technical Indicator Summary")

            latest_ma20 = history["MA20"].iloc[-1]
            latest_ma50 = history["MA50"].iloc[-1]

            col10, col11 = st.columns(2)

            col10.metric(
                "20-Day Moving Average",
                f"${latest_ma20:.2f}" if pd.notna(latest_ma20) else "N/A"
            )

            col11.metric(
                "50-Day Moving Average",
                f"${latest_ma50:.2f}" if pd.notna(latest_ma50) else "N/A"
            )

            if pd.notna(latest_ma20) and pd.notna(latest_ma50):
                if latest_ma20 > latest_ma50:
                    st.success("Bullish Signal: MA20 is above MA50.")
                else:
                    st.warning("Bearish Signal: MA20 is below MA50.")
            else:
                st.info("Not enough data for moving average signal.")

            st.divider()

            if comparison_ticker:
                comparison_info, comparison_history = load_stock_data(
                    comparison_ticker,
                    period
                )

                if comparison_history.empty:
                    st.error("Invalid comparison ticker symbol.")
                else:
                    comparison_current_price, comparison_change_pct = (
                        calculate_price_change(comparison_history)
                    )

                    st.subheader(f"{ticker} vs {comparison_ticker}")

                    compare_col1, compare_col2 = st.columns(2)

                    compare_col1.metric(
                        f"{ticker} Current Price",
                        f"${current_price:.2f}",
                        f"{price_change_pct:.2f}%"
                    )

                    compare_col2.metric(
                        f"{comparison_ticker} Current Price",
                        f"${comparison_current_price:.2f}",
                        f"{comparison_change_pct:.2f}%"
                    )

                    comparison_chart = history[["Close"]].rename(
                        columns={"Close": ticker}
                    )

                    comparison_chart = comparison_chart.join(
                        comparison_history[["Close"]].rename(
                            columns={"Close": comparison_ticker}
                        ),
                        how="inner"
                    )

                    st.line_chart(comparison_chart)

                    comparison_table = pd.DataFrame(
                        {
                            "Metric": [
                                "Company",
                                "Market Cap",
                                "P/E Ratio",
                                "Volume",
                                "Sector"
                            ],
                            ticker: [
                                info.get("longName", ticker),
                                f"${info.get('marketCap', 0):,}",
                                info.get("trailingPE", "N/A"),
                                f"{info.get('volume', 0):,}",
                                info.get("sector", "N/A")
                            ],
                            comparison_ticker: [
                                comparison_info.get(
                                    "longName",
                                    comparison_ticker
                                ),
                                f"${comparison_info.get('marketCap', 
0):,}",
                                comparison_info.get("trailingPE", "N/A"),
                                f"{comparison_info.get('volume', 0):,}",
                                comparison_info.get("sector", "N/A")
                            ]
                        }
                    )

                    st.dataframe(comparison_table)

            st.divider()

            st.subheader("Export Stock Data")

            csv_data = history.to_csv().encode("utf-8")

            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name=f"{ticker}_{period}_stock_data.csv",
                mime="text/csv",
                key="download_csv"
            )

            if show_recent_data:
                st.subheader("Recent Trading Data")
                st.dataframe(history.tail(15))

    except Exception as e:
        st.error(f"Error retrieving data: {e}")
PY
