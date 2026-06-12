from __future__ import annotations

import pandas as pd
import streamlit as st


def render_price_chart(history, ticker):
    st.subheader("Price History")

    if history is None or history.empty:
        st.info("No price history available.")
        return

    if "Date" not in history.columns or "Close" not in history.columns:
        st.info("Price chart requires Date and Close columns.")
        return

    chart_data = history[["Date", "Close"]].copy()

    chart_data["Date"] = pd.to_datetime(
        chart_data["Date"],
        errors="coerce"
    )

    chart_data["Close"] = pd.to_numeric(
        chart_data["Close"],
        errors="coerce"
    )

    chart_data = chart_data.dropna(subset=["Date", "Close"])
    chart_data = chart_data.sort_values("Date")

    if chart_data.empty:
        st.info("No usable price history available.")
        return

    chart_data = chart_data.set_index("Date")

    st.line_chart(chart_data["Close"])


def render_comparison_chart(
    history,
    comparison_history,
    ticker,
    comparison_ticker
):
    st.subheader("Stock Comparison")

    if history is None or history.empty:
        st.info("Primary stock history is not available.")
        return

    if comparison_history is None or comparison_history.empty:
        st.info("Comparison stock history is not available.")
        return

    required_columns = ["Date", "Close"]

    for column in required_columns:
        if column not in history.columns:
            st.info("Primary stock comparison requires Date and Close columns.")
            return

        if column not in comparison_history.columns:
            st.info("Comparison stock requires Date and Close columns.")
            return

    primary = history[["Date", "Close"]].copy()
    comparison = comparison_history[["Date", "Close"]].copy()

    primary["Date"] = pd.to_datetime(
        primary["Date"],
        errors="coerce"
    )

    comparison["Date"] = pd.to_datetime(
        comparison["Date"],
        errors="coerce"
    )

    primary["Close"] = pd.to_numeric(
        primary["Close"],
        errors="coerce"
    )

    comparison["Close"] = pd.to_numeric(
        comparison["Close"],
        errors="coerce"
    )

    primary = primary.dropna(subset=["Date", "Close"])
    comparison = comparison.dropna(subset=["Date", "Close"])

    if primary.empty or comparison.empty:
        st.info("Not enough clean data to render comparison chart.")
        return

    primary = primary.sort_values("Date")
    comparison = comparison.sort_values("Date")

    primary = primary.rename(columns={"Close": ticker})
    comparison = comparison.rename(columns={"Close": comparison_ticker})

    chart_data = primary.merge(
        comparison,
        on="Date",
        how="inner"
    )

    if chart_data.empty:
        st.info("No overlapping dates available for comparison.")
        return

    chart_data = chart_data.set_index("Date")

    st.line_chart(chart_data[[ticker, comparison_ticker]])

def make_arrow_safe(dataframe):
    safe_dataframe = dataframe.copy()

    for column in safe_dataframe.columns:
        if safe_dataframe[column].dtype == "object":
            safe_dataframe[column] = safe_dataframe[column].astype(str)

    return safe_dataframe


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

    st.dataframe(make_arrow_safe(comparison_table))

