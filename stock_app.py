import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Stock Analysis Dashboard",
    layout="wide"
)

st.title("Stock Analysis Dashboard")
st.caption("Sprint 3: Sidebar Controls and CSV Export")

st.sidebar.header("Dashboard Controls")

ticker = st.sidebar.text_input(
    "Enter Stock Ticker",
    value="AAPL",
    key="ticker_input"
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

if ticker:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        history = stock.history(period=period)

        if history.empty:
            st.error(
             "Invalid ticker symbol. Try AAPL, MSFT, NVDA, TSLA, or AMZN."
            )
        else:
            history["MA20"] = history["Close"].rolling(window=20).mean()
            history["MA50"] = history["Close"].rolling(window=50).mean()

            current_price = history["Close"].iloc[-1]
            previous_close = history["Close"].iloc[-2]

            price_change = current_price - previous_close
            price_change_pct = (price_change / previous_close) * 100

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

            chart_data = history[
                [
                    "Close",
                    "MA20",
                    "MA50"
                ]
            ]

            st.line_chart(chart_data)

            st.divider()

            st.subheader("Technical Indicator Summary")

            latest_ma20 = history["MA20"].iloc[-1]
            latest_ma50 = history["MA50"].iloc[-1]

            col10, col11 = st.columns(2)

            col10.metric(
                "20-Day Moving Average",
                f"${latest_ma20:.2f}" if latest_ma20 else "N/A"
            )

            col11.metric(
                "50-Day Moving Average",
                f"${latest_ma50:.2f}" if latest_ma50 else "N/A"
            )

            if latest_ma20 > latest_ma50:
                st.success("Bullish Signal: MA20 is above MA50.")
            else:
                st.warning("Bearish Signal: MA20 is below MA50.")

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
