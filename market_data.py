from __future__ import annotations

from typing import Any

import pandas as pd
import requests
import streamlit as st

from database import get_cached_market_data
from database import save_market_data_cache


BASE_URL = "https://www.alphavantage.co/query"

CACHE_TTL_SECONDS = 21600

PERIOD_ROW_LIMITS = {
    "1mo": 22,
    "3mo": 66,
    "6mo": 132,
    "1y": 252,
    "5y": 1260,
}


def get_alpha_vantage_key() -> str | None:
    try:
        api_key = st.secrets.get("ALPHA_VANTAGE_API_KEY")
    except Exception:
        api_key = None

    if not api_key:
        return None

    return str(api_key).strip()


def clean_ticker_symbol(ticker: Any) -> str:
    if ticker is None:
        return ""

    return str(ticker).upper().strip()


def is_valid_ticker_format(ticker: Any) -> tuple[bool, str]:
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


def validate_ticker(ticker: Any) -> tuple[bool, str]:
    """
    Local validation only.

    First principle:
    Validation should not burn market-data API calls.
    Market data lookup will prove whether the symbol has usable data.
    """
    return is_valid_ticker_format(ticker)


def apply_period_filter(history: pd.DataFrame, period: str) -> pd.DataFrame:
    if history is None or history.empty:
        return pd.DataFrame()

    row_limit = PERIOD_ROW_LIMITS.get(period)

    if row_limit:
        return history.tail(row_limit).reset_index(drop=True)

    return history.reset_index(drop=True)


def normalize_market_dataframe(history: pd.DataFrame) -> pd.DataFrame:
    if history is None or history.empty:
        return pd.DataFrame()

    normalized = history.copy()

    required_columns = [
        "Date",
        "Open",
        "High",
        "Low",
        "Close",
        "Adjusted Close",
        "Volume",
    ]

    for column in required_columns:
        if column not in normalized.columns:
            normalized[column] = None

    normalized = normalized[required_columns]

    normalized["Date"] = pd.to_datetime(
        normalized["Date"],
        errors="coerce"
    )

    numeric_columns = [
        "Open",
        "High",
        "Low",
        "Close",
        "Adjusted Close",
        "Volume",
    ]

    for column in numeric_columns:
        normalized[column] = pd.to_numeric(
            normalized[column],
            errors="coerce"
        )

    normalized = normalized.dropna(subset=["Date", "Close"])
    normalized = normalized.sort_values("Date")
    normalized = normalized.reset_index(drop=True)

    return normalized


def cached_rows_to_dataframe(cached_rows: list[Any]) -> pd.DataFrame:
    if not cached_rows:
        return pd.DataFrame()

    rows = []

    for row in cached_rows:
        rows.append(
            {
                "Date": row.price_date,
                "Open": row.open_price,
                "High": row.high_price,
                "Low": row.low_price,
                "Close": row.close_price,
                "Adjusted Close": row.close_price,
                "Volume": row.volume,
            }
        )

    return normalize_market_dataframe(pd.DataFrame(rows))


def parse_alpha_vantage_error(data: dict[str, Any]) -> str | None:
    if "Information" in data:
        return str(data["Information"])

    if "Note" in data:
        return str(data["Note"])

    if "Error Message" in data:
        return str(data["Error Message"])

    return None


def parse_alpha_vantage_daily_response(
    ticker: str,
    data: dict[str, Any]
) -> tuple[pd.DataFrame, str | None]:
    provider_error = parse_alpha_vantage_error(data)

    if provider_error:
        return pd.DataFrame(), provider_error

    time_series = data.get("Time Series (Daily)")

    if not time_series:
        return pd.DataFrame(), "No market data found for " + ticker

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
                "Volume": values.get("5. volume"),
            }
        )

    history = normalize_market_dataframe(pd.DataFrame(rows))

    if history.empty:
        return pd.DataFrame(), "No usable close price data found for " + ticker

    return history, None


def fetch_alpha_vantage_daily_data(ticker: str) -> tuple[pd.DataFrame, str | None]:
    api_key = get_alpha_vantage_key()

    if not api_key:
        return pd.DataFrame(), "Missing Alpha Vantage API key."

    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": ticker,
        "outputsize": "compact",
        "apikey": api_key,
    }

    try:
        response = requests.get(
            BASE_URL,
            params=params,
            timeout=15
        )

        response.raise_for_status()
        data = response.json()

        return parse_alpha_vantage_daily_response(ticker, data)

    except requests.exceptions.Timeout:
        return pd.DataFrame(), "Market data request timed out for " + ticker

    except requests.exceptions.RequestException as error:
        return (
            pd.DataFrame(),
            "Market data request error for " + ticker + ": " + str(error)
        )

    except Exception as error:
        return (
            pd.DataFrame(),
            "Market data error for " + ticker + ": " + str(error)
        )


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_stock_data(
    ticker: Any,
    period: str = "6mo",
    force_refresh: bool = False
) -> tuple[pd.DataFrame, str | None]:
    clean_ticker = clean_ticker_symbol(ticker)

    is_valid_format, format_result = is_valid_ticker_format(clean_ticker)

    if not is_valid_format:
        return pd.DataFrame(), format_result

    if not force_refresh:
        cached_rows = get_cached_market_data(clean_ticker)
        cached_history = cached_rows_to_dataframe(cached_rows)

        if not cached_history.empty:
            filtered_history = apply_period_filter(
                cached_history,
                period
            )

            if not filtered_history.empty:
                return filtered_history, None

    fresh_history, error = fetch_alpha_vantage_daily_data(clean_ticker)

    if error:
        return pd.DataFrame(), error

    save_success, cache_message = save_market_data_cache(
        clean_ticker,
        fresh_history
    )

    if not save_success:
        # Do not fail the app because cache saving failed.
        # The fresh market data is still usable.
        pass

    filtered_history = apply_period_filter(
        fresh_history,
        period
    )

    if filtered_history.empty:
        return pd.DataFrame(), "No usable market data found for " + clean_ticker

    return filtered_history, None


def load_stock_data(
    ticker: Any,
    period: str = "6mo",
    force_refresh: bool = False
) -> tuple[dict[str, Any], pd.DataFrame, str | None]:
    history, error = get_stock_data(
        ticker,
        period,
        force_refresh=force_refresh
    )

    info = {
        "ticker": clean_ticker_symbol(ticker),
        "source": "Neon Cache / Alpha Vantage",
        "period": period,
    }

    if error:
        return info, history, error

    return info, history, None


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_current_price(ticker: Any) -> float | None:
    clean_ticker = clean_ticker_symbol(ticker)

    is_valid_format, _ = is_valid_ticker_format(clean_ticker)

    if not is_valid_format:
        return None

    history, error = get_stock_data(clean_ticker, period="1mo")

    if error or history.empty:
        return None

    if "Close" not in history.columns:
        return None

    latest_close = history["Close"].dropna()

    if latest_close.empty:
        return None

    return float(latest_close.iloc[-1])


def get_latest_price(ticker: Any) -> float | None:
    return get_current_price(ticker)


def calculate_price_change(history: pd.DataFrame) -> tuple[float, float]:
    if history is None or history.empty:
        return 0, 0

    if "Close" not in history.columns:
        return 0, 0

    close_prices = history["Close"].dropna()

    if len(close_prices) < 2:
        return 0, 0

    first_price = float(close_prices.iloc[0])
    last_price = float(close_prices.iloc[-1])

    price_change = last_price - first_price

    if first_price == 0:
        percent_change = 0
    else:
        percent_change = (price_change / first_price) * 100

    return price_change, percent_change


def get_stock_volatility(ticker: Any) -> float:
    history, error = get_stock_data(ticker, period="6mo")

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

    return float(volatility)


def clear_market_data_cache() -> None:
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
