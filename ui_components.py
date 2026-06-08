import pandas as pd
import streamlit as st

from database import add_portfolio_position
from database import add_to_watchlist
from database import get_portfolio_positions
from database import get_watchlist
from database import remove_portfolio_position
from database import remove_from_watchlist
from indicators import get_macd_signal
from indicators import get_rsi_signal
from indicators import get_volatility_signal
from portfolio import calculate_portfolio_risk_score
from portfolio import calculate_risk_reward
from portfolio import calculate_stop_loss
from portfolio import calculate_target_price
from portfolio import format_portfolio_dataframe


def render_watchlist_sidebar(ticker):
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


def render_portfolio_sidebar():
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

        submitted_position = st.form_submit_button("Add Position")

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

    return portfolio_positions


def render_portfolio_dashboard(portfolio_df):
    st.subheader("Portfolio Analytics")

    if portfolio_df.empty:
        st.info("Add a portfolio position from the sidebar.")
        return

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

    render_risk_dashboard(portfolio_df, largest_position)
    render_portfolio_table(portfolio_df)


def render_risk_dashboard(portfolio_df, largest_position):
    st.subheader("Portfolio Risk Dashboard")

    risk_score, risk_label = calculate_portfolio_risk_score(
        portfolio_df
    )

    average_volatility = portfolio_df["Volatility %"].mean()
    max_allocation = portfolio_df["Allocation %"].max()
    position_count = len(portfolio_df)

    risk_col1, risk_col2, risk_col3 = st.columns(3)

    risk_col1.metric(
        "Portfolio Risk Score",
        str(risk_score) + "/100",
        risk_label
    )

    risk_col2.metric(
        "Average Volatility",
        f"{average_volatility:.2f}%"
    )

    risk_col3.metric(
        "Number of Positions",
        position_count
    )

    risk_col4, risk_col5, risk_col6 = st.columns(3)

    highest_volatility = portfolio_df.sort_values(
        by="Volatility %",
        ascending=False
    ).iloc[0]["Ticker"]

    risk_col4.metric(
        "Largest Allocation",
        largest_position["Ticker"],
        f"{max_allocation:.2f}%"
    )

    risk_col5.metric(
        "Highest Volatility",
        highest_volatility
    )

    risk_col6.metric(
        "Risk Label",
        risk_label
    )

    if risk_label == "High Risk":
        st.warning(
            "Portfolio risk is high. Review concentration, volatility, "
            "and position count."
        )
    elif risk_label == "Moderate Risk":
        st.info("Portfolio risk is moderate.")
    else:
        st.success(
            "Portfolio risk appears lower based on current inputs."
        )

    if max_allocation >= 50:
        st.warning(
            largest_position["Ticker"]
            + " represents more than 50% of the portfolio."
        )
    elif max_allocation >= 35:
        st.info(
            largest_position["Ticker"]
            + " is a major portfolio concentration."
        )
    else:
        st.success("Portfolio concentration risk is moderate.")

    st.subheader("Volatility by Holding")

    volatility_chart = portfolio_df.set_index("Ticker")[
        ["Volatility %"]
    ]

    st.bar_chart(volatility_chart)

    st.subheader("Portfolio Allocation")

    allocation_chart = portfolio_df.set_index("Ticker")[
        ["Current Value"]
    ]

    st.bar_chart(allocation_chart)

    render_stop_loss_calculator(portfolio_df)


def render_stop_loss_calculator(portfolio_df):
    st.subheader("Stop-Loss and Target Calculator")

    calculator_col1, calculator_col2, calculator_col3 = st.columns(3)

    calculator_ticker = calculator_col1.selectbox(
        "Select Position",
        options=portfolio_df["Ticker"].tolist(),
        key="risk_calculator_ticker"
    )

    stop_loss_pct = calculator_col2.number_input(
        "Stop-Loss %",
        min_value=1.0,
        max_value=90.0,
        value=10.0,
        step=1.0,
        key="stop_loss_pct_input"
    )

    target_gain_pct = calculator_col3.number_input(
        "Target Gain %",
        min_value=1.0,
        max_value=500.0,
        value=20.0,
        step=1.0,
        key="target_gain_pct_input"
    )

    selected_row = portfolio_df[
        portfolio_df["Ticker"] == calculator_ticker
    ].iloc[0]

    current_price = selected_row["Current Price"]

    stop_price = calculate_stop_loss(current_price, stop_loss_pct)
    target_price = calculate_target_price(current_price, target_gain_pct)

    risk_reward_ratio = calculate_risk_reward(
        current_price,
        stop_price,
        target_price
    )

    calc_col1, calc_col2, calc_col3, calc_col4 = st.columns(4)

    calc_col1.metric("Current Price", f"${current_price:,.2f}")
    calc_col2.metric("Stop-Loss Price", f"${stop_price:,.2f}")
    calc_col3.metric("Target Price", f"${target_price:,.2f}")
    calc_col4.metric("Risk/Reward Ratio", f"{risk_reward_ratio:.2f}")

    if risk_reward_ratio >= 2:
        st.success("Risk/reward profile is favorable.")
    elif risk_reward_ratio >= 1:
        st.info("Risk/reward profile is balanced.")
    else:
        st.warning("Risk/reward profile is weak.")


def render_portfolio_table(portfolio_df):
    st.subheader("Portfolio Performance Table")

    sort_option = st.selectbox(
        "Sort Portfolio By",
        options=[
            "Ticker",
            "Current Value",
            "Gain/Loss",
            "Gain/Loss %",
            "Allocation %",
            "Volatility %"
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
        file_name="portfolio_risk_dashboard.csv",
        mime="text/csv",
        key="download_portfolio_csv"
    )


def render_stock_header(info, ticker, current_price, price_change_pct):
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


def render_company_profile(info, show_company_overview):
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


def render_technical_indicators(history, volatility):
    st.divider()
    st.subheader("Price and Moving Averages")

    chart_data = history[["Close", "MA20", "MA50"]]
    st.line_chart(chart_data)

    st.divider()
    st.subheader("Technical Indicator Summary")

    latest_rsi = history["RSI"].iloc[-1]
    latest_macd = history["MACD"].iloc[-1]
    latest_signal = history["Signal Line"].iloc[-1]
    latest_daily_return = history["Daily Return %"].iloc[-1]
    latest_ma20 = history["MA20"].iloc[-1]
    latest_ma50 = history["MA50"].iloc[-1]

    rsi_signal = get_rsi_signal(latest_rsi)
    macd_signal = get_macd_signal(latest_macd, latest_signal)
    volatility_signal = get_volatility_signal(volatility)

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

    tech_col4.metric(
        "20-Day Moving Average",
        f"${latest_ma20:.2f}" if pd.notna(latest_ma20) else "N/A"
    )

    tech_col5.metric(
        "50-Day Moving Average",
        f"${latest_ma50:.2f}" if pd.notna(latest_ma50) else "N/A"
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
    st.line_chart(history[["RSI"]])

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
    st.line_chart(history[["Daily Return %"]])


def render_stock_comparison(
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
):
    st.divider()
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
                f"${comparison_info.get('marketCap', 0):,}",
                comparison_info.get("trailingPE", "N/A"),
                f"{comparison_info.get('volume', 0):,}",
                comparison_info.get("sector", "N/A")
            ]
        }
    )

    st.dataframe(comparison_table)


def render_stock_export(history, ticker, period, show_recent_data):
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
