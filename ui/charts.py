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
