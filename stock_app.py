import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Stock Analysis Dashboard",
    layout="wide"
)

st.title("Stock Analysis Dashboard")

ticker = st.text_input(
    "Enter Stock Ticker",
    value="AAPL",
    key="ticker_input"
).upper().strip()

if ticker:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        history = stock.history(period="30d")

        if history.empty:
            st.error("Invalid ticker symbol")
        else:
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
                "P/E Ratio",
                f"{info.get('trailingPE', 0):.2f}"
            )

            st.write("Sector:", info.get("sector", "N/A"))
            st.write("Industry:", info.get("industry", "N/A"))

            st.subheader("Company Overview")
            st.write(
                info.get(
                    "longBusinessSummary",
                    "No company description available."
                )
            )

            st.subheader("30-Day Closing Price Chart")
            st.line_chart(history["Close"])

            st.subheader("Recent Price Data")
            st.dataframe(history.tail())

    except Exception as e:
        st.error(f"Error retrieving data: {e}")
