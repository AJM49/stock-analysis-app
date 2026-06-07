import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(
    page_title="Stock Analysis Dashboard",
    layout="wide"
)

st.title("Stock Analysis Dashboard")
st.caption("Sprint 2: Technical Analysis Dashboard")

ticker = st.text_input(
    "Enter Stock Ticker",
    value="AAPL",
    key="ticker_input"
).upper().strip()

if ticker:

    try:

        stock = yf.Ticker(ticker)
        info = stock.info

        history = stock.history(period="6mo")

        if history.empty:

            st.error(
                "Invalid ticker symbol."
            )

        else:

            history["MA20"] = (
                history["Close"]
                .rolling(window=20)
                .mean()
            )

            history["MA50"] = (
                history["Close"]
                .rolling(window=50)
                .mean()
            )

            current_price = history["Close"].iloc[-1]
            previous_close = history["Close"].iloc[-2]

            price_change = current_price - previous_close
            price_change_pct = (
                price_change / previous_close
            ) * 100

            st.subheader(
                info.get("longName", ticker)
            )

            # Primary Metrics

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

            # Secondary Metrics

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

            # Valuation Metrics

            col7, col8, col9 = st.columns(3)

            pe_ratio = info.get("trailingPE")
            dividend_yield = info.get("dividendYield")
            beta = info.get("beta")

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

            st.write(
                "Sector:",
                info.get("sector", "N/A")
            )

            st.write(
                "Industry:",
                info.get("industry", "N/A")
            )

            st.subheader("Company Overview")

            st.write(
                info.get(
                    "longBusinessSummary",
                    "No company description available."
                )
            )

            st.divider()

            st.subheader(
                "Price and Moving Averages"
            )

            chart_data = history[
                [
                    "Close",
                    "MA20",
                    "MA50"
                ]
            ]

            st.line_chart(chart_data)

            st.divider()

            st.subheader(
                "Technical Indicator Summary"
            )

            latest_ma20 = history["MA20"].iloc[-1]
            latest_ma50 = history["MA50"].iloc[-1]

            col10, col11 = st.columns(2)

            col10.metric(
                "20-Day Moving Average",
                f"${latest_ma20:.2f}"
            )

            col11.metric(
                "50-Day Moving Average",
                f"${latest_ma50:.2f}"
            )

            if latest_ma20 > latest_ma50:
                st.success(
                    "Bullish Signal: MA20 is above MA50."
                )
            else:
                st.warning(
                    "Bearish Signal: MA20 is below MA50."
                )

            st.divider()

            st.subheader(
                "Recent Trading Data"
            )

            st.dataframe(
                history.tail(15)
            )

    except Exception as e:

        st.error(
            f"Error retrieving data: {e}"
        )
