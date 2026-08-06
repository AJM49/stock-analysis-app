
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from indicators import (
    get_macd_signal,
    get_rsi_signal,
    get_volatility_signal,
)

def get_rsi_signal(rsi_value):
    if rsi_value is None:
        return "Neutral"

    try:
        rsi_value = float(rsi_value)
    except (TypeError, ValueError):
        return "Neutral"

    if rsi_value >= 70:
        return "Overbought"
    if rsi_value <= 30:
        return "Oversold"

    return "Neutral"


def get_macd_signal(macd_value, signal_value):
    if macd_value is None or signal_value is None:
        return "Neutral"

    try:
        macd_value = float(macd_value)
        signal_value = float(signal_value)
    except (TypeError, ValueError):
        return "Neutral"

    if macd_value > signal_value:
        return "Bullish"
    if macd_value < signal_value:
        return "Bearish"

    return "Neutral"


def get_moving_average_signal(current_price, moving_average):
    if current_price is None or moving_average is None:
        return "Neutral"

    try:
        current_price = float(current_price)
        moving_average = float(moving_average)
    except (TypeError, ValueError):
        return "Neutral"

    if current_price > moving_average:
        return "Bullish"
    if current_price < moving_average:
        return "Bearish"

    return "Neutral"
def get_market_data_freshness(history):
    """
    Return the latest market date, age in days,
    and freshness status.
    """
    if history is None or history.empty:
        return None, None, "Unavailable"

    if "Date" not in history.columns:
        return None, None, "Unavailable"

    date_values = pd.to_datetime(
        history["Date"],
        errors="coerce",
    ).dropna()

    if date_values.empty:
        return None, None, "Unavailable"

    latest_market_date = date_values.max().date()
    age_days = (date.today() - latest_market_date).days

    if age_days <= 3:
        status = "Fresh"
    elif age_days <= 7:
        status = "Delayed"
    else:
        status = "Stale"

    return latest_market_date, age_days, status

def render_stock_header(
    info,
    ticker,
    latest_close,
    price_change_pct,
    history=None,
cache_only=False,
):
    company_name = info.get("longName") or ticker
    st.subheader(company_name)

    selected_period_high = None
    selected_period_low = None

    if history is not None and not history.empty:
        if "High" in history.columns:
            high_values = pd.to_numeric(
                history["High"],
                errors="coerce",
            ).dropna()

            if not high_values.empty:
                selected_period_high = float(high_values.max())

        if "Low" in history.columns:
            low_values = pd.to_numeric(
                history["Low"],
                errors="coerce",
            ).dropna()

            if not low_values.empty:
                selected_period_low = float(low_values.min())

    provider_high = info.get("fiftyTwoWeekHigh")
    provider_low = info.get("fiftyTwoWeekLow")

    high_value = (
        provider_high
        if provider_high is not None
        else selected_period_high
    )

    low_value = (
        provider_low
        if provider_low is not None
        else selected_period_low
    )

    high_label = (
        "52-Week High"
        if provider_high is not None
        else "Selected-Period High"
    )

    low_label = (
        "52-Week Low"
        if provider_low is not None
        else "Selected-Period Low"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Latest Daily Close",
        f"${latest_close:.2f}",
        f"{price_change_pct:.2f}%",
        help=(
            "The latest available daily closing price. "
            "This is not a real-time market quote."
        ),
    )

    col2.metric(
        high_label,
        f"${float(high_value):.2f}"
        if high_value is not None
        else "N/A",
    )

    col3.metric(
        low_label,
        f"${float(low_value):.2f}"
        if low_value is not None
        else "N/A",
    )

    col4, col5, col6 = st.columns(3)

    market_cap = info.get("marketCap")

    volume = None
    average_volume = None

    if (
        history is not None
        and not history.empty
        and "Volume" in history.columns
    ):
        volume_series = history["Volume"].dropna()

        if not volume_series.empty:
            volume = volume_series.iloc[-1]
            average_volume = volume_series.mean()

    col4.metric(
        "Market Cap",
        f"${float(market_cap):,.0f}"
        if market_cap is not None
        else "N/A",
    )

    col5.metric(
        "Volume",
        f"{float(volume):,.0f}"
        if volume is not None
        else "N/A",
    )

    col6.metric(
        "Average Volume",
        f"{float(average_volume):,.0f}"
        if average_volume is not None
        else "N/A",
    )

    pe_ratio = info.get("trailingPE")
    dividend_yield = info.get("dividendYield")
    beta = info.get("beta")

    col7, col8, col9 = st.columns(3)

    col7.metric(
        "P/E Ratio",
        f"{float(pe_ratio):.2f}"
        if pe_ratio is not None
        else "N/A",
    )

    col8.metric(
        "Dividend Yield",
        f"{float(dividend_yield) * 100:.2f}%"
        if dividend_yield is not None
        else "N/A",
    )

    col9.metric(
        "Beta",
        f"{float(beta):.2f}"
        if beta is not None
        else "N/A",
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

