import pandas as pd
import streamlit as st
import yfinance as yf

from database import add_portfolio_position
from database import add_to_watchlist
from database import get_portfolio_positions
from database import get_watchlist
from database import init_database
from database import remove_portfolio_position
from database import remove_from_watchlist


st.set_page_config(
    page_title="Stock Analysis Dashboard",
    layout="wide"
)

init_database()

st.title("Stock Analysis Dashboard")
st.caption("Sprint 7: Technical Indicators")

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
    change = current_price - previous_close
    change_pct = (change / previous_close) * 100
    return current_price, change_pct


def get_latest_price(symbol):
    stock = yf.Ticker(symbol)
    history = stock.history(period="5d")

    if history.empty:
        return None

    latest_price = history["Close"].iloc[-1]
    return float(latest_price)


def calculate_rsi(history, window=14):
    delta = history["Close"].diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    average_gain = gains.rolling(window=window).mean()
    average_loss = losses.rolling(window=window).mean()

    relative_strength = average_gain / average_loss
    rsi = 100 - (100 / (1 + relative_strength))

    return rsi


def calculate_macd(history):
    ema_12 = history["Close"].ewm(
        span=12,
        adjust=False
    ).mean()

    ema_26 = history["Close"].ewm(
        span=26,
        adjust=False
    ).mean()

    macd_line = ema_12 - ema_26

    signal_line = macd_line.ewm(
        span=9,
        adjust=False
    ).mean()

    macd_histogram = macd_line - signal_line

    return macd_line, signal_line, macd_histogram


def calculate_volatility(history):
    daily_returns = history["Close"].pct_change()
    volatility = daily_returns.std() * 100
    return daily_returns, volatility


def get_rsi_signal(rsi_value):
    if pd.isna(rsi_value):
        return "Not enough data"

    if rsi_value >= 70:
        return "Overbought"

    if rsi_value <= 30:
        return "Oversold"

    return "Neutral"


def get_macd_signal(macd_value, signal_value):
    if pd.isna(macd_value) or pd.isna(signal_value):
        return "Not enough data"

    if macd_value > signal_value:
        return "Bullish momentum"

    if macd_value < signal_value:
        return "Bearish momentum"

    return "Neutral momentum"


def get_volatility_signal(volatility_value):
    if pd.isna(volatility_value):
        return "Not enough data"

    if volatility_value >= 3:
        return "High volatility"

    if volatility_value >= 1.5:
        return "Moderate volatility"

    return "Low volatility"


def build_portfolio_dataframe(portfolio_positions):
    portfolio_rows = []

    for position in portfolio_positions:
        current_price = get_latest_price(position.ticker)

        if current_price is None:
            current_price = 0.0

        cost_basis = position.shares * position.buy_price
        current_value = position.shares * current_price
        gain_loss = current_value - cost_basis

        if cost_basis > 0:
            gain_loss_pct = (gain_loss / cost_basis) * 100
        else:
            gain_loss_pct = 0.0

        portfolio_rows.append(
            {
                "Ticker": position.ticker,
                "Shares": position.shares,
                "Buy Price": position.buy_price,
                "Current Price": current_price,
                "Cost Basis": cost_basis,
                "Current Value": current_value,
                "Gain/Loss": gain_loss,
                "Gain/Loss %": gain_loss_pct
            }
        )

    portfolio_df = pd.DataFrame(portfolio_rows)

    if portfolio_df.empty:
        return portfolio_df

    total_current_value = portfolio_df["Current Value"].sum()

    if total_current_value > 0:
        portfolio_df["Allocation %"] = (
            portfolio_df["Current Value"] / total_current_value
        ) * 100
    else:
        portfolio_df["Allocation %"] = 0.0

    return portfolio_df


def format_portfolio_dataframe(portfolio_df):
    formatted_df = portfolio_df.copy()

    money_columns = [
        "Buy Price",
        "Current Price",
        "Cost Basis",
        "Current Value",
        "Gain/Loss"
    ]

    for column in money_columns:
        formatted_df[column] = formatted_df[column].map(
            lambda value: f"${value:,.2f}"
        )

    percent_columns = [
        "Gain/Loss %",
        "Allocation %"
    ]

    for column in percent_columns:
        formatted_df[column] = formatted_df[column].map(
            lambda value: f"{value:.2f}%"
        )

    return formatted_df


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
    saved_tickers = [stock.ticker for stock in watchlist_items]

    selected_watchlist_ticker = st.sidebar.selectbox(
        "Saved Tickers",
        options=saved_tickers,
        key="saved_tickers_select"
    )

    if st.sidebar.button(
        "Remove Selected Ticker",
        key="remove_selected_ticker"
    ):
        success, message = remove_from_watchlist(
            selected_watchlist_ticker
        )

        if success:
            st.sidebar.success(message)
            st.rerun()
        else:
            st.sidebar.warning(message)
else:
    st.sidebar.info("No saved tickers yet.")


st.sidebar.divider()
st.sidebar.header("Portfolio Tracker")

with st.sidebar.form("add_portfolio_position_form"):
    portfolio_ticker = st.text_input(
        "Portfolio Ticker",
        value="AAPL",
        key="portfolio_ticker_input"
    ).upper().strip()

    portfolio_shares = st.number_input(
        "Shares",
        min_value=0.0,
        value=1.0,
        step=1.0,
        format="%.4f",
        key="portfolio_shares_input"
    )

    portfolio_buy_price = st.number_input(
        "Buy Price",
        min_value=0.0,
        value=100.0,
        step=1.0,
        format="%.2f",
        key="portfolio_buy_price_input"
    )

    submitted_position = st.form_submit_button(
        "Add Position"
    )

    if submitted_position:
        success, message = add_portfolio_position(
            portfolio_ticker,
            portfolio_shares,
            portfolio_buy_price
        )

        if success:
            st.success(message)
        else:
            st.warning(message)

portfolio_positions = get_portfolio_positions()

if portfolio_positions:
    portfolio_tickers = [
        position.ticker for position in portfolio_positions
    ]

    selected_position_ticker = st.sidebar.selectbox(
        "Portfolio Positions",
        options=portfolio_tickers,
        key="portfolio_positions_select"
    )

    if st.sidebar.button(
        "Remove Portfolio Position",
        key="remove_portfolio_position"
    ):
        success, message = remove_portfolio_position(
            selected_position_ticker
        )

        if success:
            st.sidebar.success(message)
            st.rerun()
        else:
            st.sidebar.warning(message)
else:
    st.sidebar.info("No portfolio positions yet.")


st.subheader("Portfolio Analytics")

portfolio_df = build_portfolio_dataframe(portfolio_positions)

if not portfolio_df.empty:
    total_cost_basis = portfolio_df["Cost Basis"].sum()
    total_current_value = portfolio_df["Current Value"].sum()
    total_gain_loss = portfolio_df["Gain/Loss"].sum()

    if total_cost_basis > 0:
        total_gain_loss_pct = (
            total_gain_loss / total_cost_basis
        ) * 100
    else:
        total_gain_loss_pct = 0.0

    best_position = portfolio_df.sort_values(
        by="Gain/Loss %",
        ascending=False
    ).iloc[0]

    worst_position = portfolio_df.sort_values(
        by="Gain/Loss %",
        ascending=True
    ).iloc[0]

    largest_position = portfolio_df.sort_values(
        by="Allocation %",
        ascending=False
    ).iloc[0]

    summary_col1, summary_col2, summary_col3 = st.columns(3)

    summary_col1.metric(
        "Total Current Value",
        f"${total_current_value:,.2f}"
    )

    summary_col2.metric(
        "Total Cost Basis",
        f"${total_cost_basis:,.2f}"
    )

    summary_col3.metric(
        "Total Gain/Loss",
        f"${total_gain_loss:,.2f}",
        f"{total_gain_loss_pct:.2f}%"
    )

    insight_col1, insight_col2, insight_col3 = st.columns(3)

    insight_col1.metric(
        "Best Performer",
        best_position["Ticker"],
        f"{best_position['Gain/Loss %']:.2f}%"
    )

    insight_col2.metric(
        "Worst Performer",
        worst_position["Ticker"],
        f"{worst_position['Gain/Loss %']:.2f}%"
    )

    insight_col3.metric(
        "Largest Allocation",
        largest_position["Ticker"],
        f"{largest_position['Allocation %']:.2f}%"
    )

    if largest_position["Allocation %"] >= 50:
        st.warning(
            largest_position["Ticker"]
            + " represents more than 50% of the portfolio."
        )
    elif largest_position["Allocation %"] >= 35:
        st.info(
            largest_position["Ticker"]
            + " is a major portfolio concentration."
        )
    else:
        st.success("Portfolio concentration risk is moderate.")

    st.subheader("Portfolio Allocation")

    allocation_chart = portfolio_df.set_index("Ticker")[
        ["Current Value"]
    ]

    st.bar_chart(allocation_chart)

    st.subheader("Portfolio Performance Table")

    sort_option = st.selectbox(
        "Sort Portfolio By",
        options=[
            "Ticker",
            "Current Value",
            "Gain/Loss",
            "Gain/Loss %",
            "Allocation %"
        ],
        index=1,
        key="portfolio_sort_option"
    )

    sort_direction = st.radio(
        "Sort Direction",
        options=[
            "Descending",
            "Ascending"
        ],
        horizontal=True,
        key="portfolio_sort_direction"
    )

    ascending_sort = sort_direction == "Ascending"

    sorted_portfolio_df = portfolio_df.sort_values(
        by=sort_option,
        ascending=ascending_sort
    )

    formatted_portfolio_df = format_portfolio_dataframe(
        sorted_portfolio_df
    )

    st.dataframe(
        formatted_portfolio_df,
        use_container_width=True
    )

    portfolio_csv = portfolio_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Portfolio CSV",
        data=portfolio_csv,
        file_name="portfolio_analytics.csv",
        mime="text/csv",
        key="download_portfolio_csv"
    )

else:
    st.info("Add a portfolio position from the sidebar.")

st.divider()


if ticker:
    try:
        info, history = load_stock_data(ticker, period)

        if history.empty:
            st.error("Invalid primary ticker symbol.")
        else:
            history["MA20"] = (
                history["Close"].rolling(window=20).mean()
            )
            history["MA50"] = (
                history["Close"].rolling(window=50).mean()
            )

            history["RSI"] = calculate_rsi(history)

            macd_line, signal_line, macd_histogram = calculate_macd(
                history
            )

            history["MACD"] = macd_line
            history["Signal Line"] = signal_line
            history["MACD Histogram"] = macd_histogram

            daily_returns, volatility = calculate_volatility(history)

            history["Daily Return %"] = daily_returns * 100

            current_price, price_change_pct = calculate_price_change(
                history
            )

            latest_rsi = history["RSI"].iloc[-1]
            latest_macd = history["MACD"].iloc[-1]
            latest_signal = history["Signal Line"].iloc[-1]
            latest_daily_return = history["Daily Return %"].iloc[-1]

            rsi_signal = get_rsi_signal(latest_rsi)
            macd_signal = get_macd_signal(latest_macd, latest_signal)
            volatility_signal = get_volatility_signal(volatility)

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
                f"{dividend_yield * 100:.2f}%"
                if dividend_yield else "N/A"
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
                overview = info.get(
                    "longBusinessSummary",
                    "No company description available."
                )
                st.write(overview)

            st.divider()

            st.subheader("Price and Moving Averages")

            chart_data = history[["Close", "MA20", "MA50"]]
            st.line_chart(chart_data)

            st.divider()

            st.subheader("Technical Indicator Summary")

            tech_col1, tech_col2, tech_col3 = st.columns(3)

            tech_col1.metric(
                "RSI",
                f"{latest_rsi:.2f}" if pd.notna(latest_rsi) else "N/A",
                rsi_signal
            )

            tech_col2.metric(
                "MACD",
                f"{latest_macd:.4f}" if pd.notna(latest_macd) else "N/A",
                macd_signal
            )

            tech_col3.metric(
                "Volatility",
                f"{volatility:.2f}%",
                volatility_signal
            )

            tech_col4, tech_col5, tech_col6 = st.columns(3)

            latest_ma20 = history["MA20"].iloc[-1]
            latest_ma50 = history["MA50"].iloc[-1]

            tech_col4.metric(
                "20-Day Moving Average",
                f"${latest_ma20:.2f}"
                if pd.notna(latest_ma20) else "N/A"
            )

            tech_col5.metric(
                "50-Day Moving Average",
                f"${latest_ma50:.2f}"
                if pd.notna(latest_ma50) else "N/A"
            )

            tech_col6.metric(
                "Latest Daily Return",
                f"{latest_daily_return:.2f}%"
                if pd.notna(latest_daily_return) else "N/A"
            )

            if pd.notna(latest_ma20) and pd.notna(latest_ma50):
                if latest_ma20 > latest_ma50:
                    st.success("Bullish Signal: MA20 is above MA50.")
                else:
                    st.warning("Bearish Signal: MA20 is below MA50.")
            else:
                st.info("Not enough data for moving average signal.")

            if rsi_signal == "Overbought":
                st.warning("RSI suggests the stock may be overbought.")
            elif rsi_signal == "Oversold":
                st.info("RSI suggests the stock may be oversold.")
            else:
                st.success("RSI is currently neutral.")

            if macd_signal == "Bullish momentum":
                st.success("MACD suggests bullish momentum.")
            elif macd_signal == "Bearish momentum":
                st.warning("MACD suggests bearish momentum.")
            else:
                st.info("MACD is neutral.")

            st.subheader("RSI Chart")

            rsi_chart = history[["RSI"]]
            st.line_chart(rsi_chart)

            st.subheader("MACD Chart")

            macd_chart = history[
                [
                    "MACD",
                    "Signal Line",
                    "MACD Histogram"
                ]
            ]

            st.line_chart(macd_chart)

            st.subheader("Daily Return Chart")

            return_chart = history[["Daily Return %"]]
            st.line_chart(return_chart)

            st.divider()

            if comparison_ticker:
                comparison_info, comparison_history = load_stock_data(
                    comparison_ticker,
                    period
                )

                if comparison_history.empty:
                    st.error("Invalid comparison ticker symbol.")
                else:
                    comp_price, comp_change_pct = calculate_price_change(
                        comparison_history
                    )

                    st.subheader(ticker + " vs " + comparison_ticker)

                    compare_col1, compare_col2 = st.columns(2)

                    compare_col1.metric(
                        ticker + " Current Price",
                        f"${current_price:.2f}",
                        f"{price_change_pct:.2f}%"
                    )

                    compare_col2.metric(
                        comparison_ticker + " Current Price",
                        f"${comp_price:.2f}",
                        f"{comp_change_pct:.2f}%"
                    )

                    comparison_chart = history[["Close"]].rename(
                        columns={"Close": ticker}
                    )

                    second_chart = comparison_history[["Close"]].rename(
                        columns={"Close": comparison_ticker}
                    )

                    comparison_chart = comparison_chart.join(
                        second_chart,
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
                label="Download Stock CSV",
                data=csv_data,
                file_name=ticker + "_" + period + "_stock_data.csv",
                mime="text/csv",
                key="download_stock_csv"
            )

            if show_recent_data:
                st.subheader("Recent Trading Data")
                st.dataframe(history.tail(15))

    except Exception as error:
        st.error("Error retrieving data: " + str(error))
