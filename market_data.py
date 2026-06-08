import logging
import re

import streamlit as st
import yfinance as yf


logging.basicConfig(
    filename="app.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


VALID_TICKER_PATTERN = re.compile(r"^[A-Z0-9.-]{1,10}$")


def validate_ticker(symbol):
    if symbol is None:
        return False, "Ticker cannot be empty."

    clean_symbol = symbol.upper().strip()

    if not clean_symbol:
        return False, "Ticker cannot be empty."

    if not VALID_TICKER_PATTERN.match(clean_symbol):
        return False, "Ticker contains invalid characters."

    return True, clean_symbol


@st.cache_data(ttl=300)
def load_stock_data(symbol, selected_period):
    is_valid, result = validate_ticker(symbol)

    if not is_valid:
        return {}, None, result

    clean_symbol = result

    try:
        stock = yf.Ticker(clean_symbol)
        info = stock.info
        history = stock.history(period=selected_period)

        if history is None or history.empty:
           return {}, None, "No market data found for " + clean_symbol + "."


        return info, history, None

    except Exception as error:
        logging.error(
            "Failed to load stock data for %s: %s",
            clean_symbol,
            str(error)
        )
        return {}, None, "Unable to retrieve data for " + clean_symbol + "."


@st.cache_data(ttl=300)
def get_latest_price(symbol):
    is_valid, result = validate_ticker(symbol)

    if not is_valid:
        return None

    clean_symbol = result

    try:
        stock = yf.Ticker(clean_symbol)
        history = stock.history(period="5d")

        if history is None or history.empty:
            return None

        latest_price = history["Close"].iloc[-1]
        return float(latest_price)

    except Exception as error:
        logging.error(
            "Failed to get latest price for %s: %s",
            clean_symbol,
            str(error)
        )
        return None


@st.cache_data(ttl=300)
def get_stock_volatility(symbol):
    is_valid, result = validate_ticker(symbol)

    if not is_valid:
        return 0.0

    clean_symbol = result

    try:
        stock = yf.Ticker(clean_symbol)
        history = stock.history(period="3mo")

        if history is None or history.empty:
            return 0.0

        daily_returns = history["Close"].pct_change()
        volatility = daily_returns.std() * 100

        if volatility != volatility:
            return 0.0

        return float(volatility)

    except Exception as error:
        logging.error(
            "Failed to get volatility for %s: %s",
            clean_symbol,
            str(error)
        )
        return 0.0


def calculate_price_change(history):
    if history is None or history.empty:
        return None, None

    if len(history) < 2:
        return None, None

    try:
        current_price = history["Close"].iloc[-1]
        previous_close = history["Close"].iloc[-2]

        if previous_close == 0:
            return float(current_price), 0.0

        change = current_price - previous_close
        change_pct = (change / previous_close) * 100

        return float(current_price), float(change_pct)

    except Exception as error:
        logging.error(
            "Failed to calculate price change: %s",
            str(error)
        )
        return None, None


def clear_market_data_cache():
    st.cache_data.clear()
