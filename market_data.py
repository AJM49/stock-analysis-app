import pandas as pd
import requests
import streamlit as st


BASE_URL = "https://www.alphavantage.co/query"


def get_alpha_vantage_key():
    try:
        api_key = st.secrets.get("ALPHA_VANTAGE_API_KEY")
    except Exception:
        api_key = None

    if not api_key:
        return None

    return str(api_key).strip()


def clean_ticker_symbol(ticker):
    if ticker is None:
        return ""

    return str(ticker).upper().strip()


def is_valid_ticker_format(ticker):
    clean_ticker = clean_ticker_symbol(ticker)

    if not clean_ticker:
        return False, "Ticker cannot be empty."

    if len(clean_ticker) > 10:
        return False, "Ticker is too long."

    allowed_characters = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ.-")

    for character in clean_ticker:
        if character not in allowed_characters:
            return False, "Ticker contains invalid characters."

    return True, clean_ticker


def validate_ticker(ticker):
    clean_ticker = clean_ticker_symbol(ticker)

    is_valid_format, format_result = is_valid_ticker_format(clean_ticker)

    if not is_valid_format:
        return False, format_result

    api_key = get_alpha_vantage_key()

    if not api_key:
        return False, "Missing Alpha Vantage API key."

    params = {
        "function": "SYMBOL_SEARCH",
        "keywords": clean_ticker,
        "apikey": api_key
    }

    try:
        response = requests.get(
            BASE_URL,
            params=params,
            timeout=15
        )

        response.raise_for_status()
        data = response.json()

        if "Information" in data:
            return False, data["Information"]

        if "Note" in data:
            return False, data["Note"]

        if "Error Message" in data:
            return False, data["Error Message"]

        matches = data.get("bestMatches", [])

        for match in matches:
            symbol = match.get("1. symbol", "").upper().strip()

            if symbol == clean_ticker:
                return True, clean_ticker

        # Fallback validation:
        # Some valid symbols may not return exact SYMBOL_SEARCH matches.
        history, error = get_stock_data(clean_ticker)

        if error:
            return False, error

        if history.empty:
            return False, "No market data found for " + clean_ticker

        return True, clean_ticker

    except Exception as error:
        return False, "Ticker validation error: " + str(error)


@st.cache_data(ttl=3600)
def get_stock_data(ticker, period="6mo"):
    clean_ticker = clean_ticker_symbol(ticker)

    is_valid_format, format_result = is_valid_ticker_format(clean_ticker)

    if not is_valid_format:
        return pd.DataFrame(), format_result

    api_key = get_alpha_vantage_key()

    if not api_key:
        return pd.DataFrame(), "Missing Alpha Vantage API key."

    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": clean_ticker,
        "outputsize": "compact",
        "apikey": api_key
    }

    try:
        response = requests.get(
            BASE_URL,
            params=params,
            timeout=15
        )

        response.raise_for_status()
        data = response.json()

        if "Information" in data:
            return pd.DataFrame(), data["Information"]

        if "Note" in data:
            return pd.DataFrame(), data["Note"]

        if "Error Message" in data:
            return pd.DataFrame(), data["Error Message"]

        time_series = data.get("Time Series (Daily)")

        if not time_series:
            return pd.DataFrame(), "No market data found for " + clean_ticker

        rows = []

        for date, values in time_series.items():
            rows.append(
                {
                    "Date": date,
                    "Open": values.get("1. open"),
                    "High": values.get("2. high"),
                    "Low": values.get("3. low"),
                    "Close": values.get("4. close"),
                    "Adjusted Close": values.get("4. close"),
                    "Volume": values.get("5. volume")
                }
            )

        history = pd.DataFrame(rows)

        if history.empty:
            return pd.DataFrame(), "No market data found for " + clean_ticker

        history["Date"] = pd.to_datetime(
            history["Date"],
            errors="coerce"
        )

        numeric_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Adjusted Close",
            "Volume"
        ]

        for column in numeric_columns:
            history[column] = pd.to_numeric(
                history[column],
                errors="coerce"
            )

        history = history.dropna(subset=["Date", "Close"])
        history = history.sort_values("Date")

        if period == "1mo":
            history = history.tail(22)
        elif period == "3mo":
            history = history.tail(66)
        elif period == "6mo":
            history = history.tail(132)
        elif period == "1y":
            history = history.tail(252)
        elif period == "5y":
            history = history.tail(1260)

        history = history.reset_index(drop=True)

        if history.empty:
            return pd.DataFrame(), "No usable close price data found for " + clean_ticker

        return history, None

    except requests.exceptions.Timeout:
        return pd.DataFrame(), "Market data request timed out for " + clean_ticker

    except requests.exceptions.RequestException as error:
        return pd.DataFrame(), "Market data request error for " + clean_ticker + ": " + str(error)

    except Exception as error:
        return pd.DataFrame(), "Market data error for " + clean_ticker + ": " + str(error)


def load_stock_data(ticker, period="6mo"):
    history, error = get_stock_data(ticker, period)

    info = {
        "ticker": clean_ticker_symbol(ticker),
        "source": "Alpha Vantage"
    }

    if error:
        return info, history, error

    return info, history, None


@st.cache_data(ttl=900)
def get_current_price(ticker):
    clean_ticker = clean_ticker_symbol(ticker)

    is_valid_format, _ = is_valid_ticker_format(clean_ticker)

    if not is_valid_format:
        return None

    api_key = get_alpha_vantage_key()

    if not api_key:
        return None

    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": clean_ticker,
        "apikey": api_key
    }

    try:
        response = requests.get(
            BASE_URL,
            params=params,
            timeout=15
        )

        response.raise_for_status()
        data = response.json()

        if "Information" in data:
            return None

        if "Note" in data:
            return None

        if "Error Message" in data:
            return None

        quote = data.get("Global Quote", {})
        price = quote.get("05. price")

        if not price:
            history, error = get_stock_data(clean_ticker)

            if error or history.empty:
                return None

            return float(history["Close"].iloc[-1])

        return float(price)

    except Exception:
        return None


def get_latest_price(ticker):
    return get_current_price(ticker)


def calculate_price_change(history):
    if history is None or history.empty:
        return 0, 0

    if "Close" not in history.columns:
        return 0, 0

    close_prices = history["Close"].dropna()

    if len(close_prices) < 2:
        return 0, 0

    first_price = close_prices.iloc[0]
    last_price = close_prices.iloc[-1]

    price_change = last_price - first_price

    if first_price == 0:
        percent_change = 0
    else:
        percent_change = (price_change / first_price) * 100

    return price_change, percent_change


def get_stock_volatility(ticker):
    history, error = get_stock_data(ticker)

    if error or history.empty:
        return 0

    if "Close" not in history.columns:
        return 0

    daily_returns = history["Close"].pct_change().dropna()

    if daily_returns.empty:
        return 0

    volatility = daily_returns.std() * (252 ** 0.5) * 100

    if pd.isna(volatility):
        return 0

    return volatility


def clear_market_data_cache():
    try:
        get_stock_data.clear()
    except Exception:
        pass

    try:
        get_current_price.clear()
    except Exception:
        pass


fetch_stock_data = get_stock_data
get_market_data = get_stock_data
