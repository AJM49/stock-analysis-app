from __future__ import annotations

import pandas as pd
import streamlit as st

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
        st.dataframe(make_arrow_safe(history.tail(15)))

