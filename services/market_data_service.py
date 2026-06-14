from __future__ import annotations

from typing import Any

import pandas as pd
import requests
import streamlit as st

from core.provider_errors import clean_provider_error_message
from core.provider_errors import is_provider_quota_error
from core.ticker import clean_ticker_symbol
from core.ticker import is_valid_ticker_format
from core.ticker import validate_ticker
from database import get_cached_market_data
from database import save_market_data_cache


BASE_URL = "https://www.alphavantage.co/query"

PERIOD_LIMITS = {
    "1mo": 22,
    "3mo": 66,
    "6mo": 132,
    "1y": 252,
    "5y": 1260,
}


REQUIRED_MARKET_COLUMNS = [
    "Date",
    "Open",
    "High",
    "Low",
    "Close",
    "Adjusted Close",
    "Volume",
]


def get_alpha_vantage_key() -> str | None:
    try:
        api_key = st.secrets.get("ALPHA_VANTAGE_API_KEY")
    except Exception:
        api_key = None

    if not api_key:
        return None

    return str(api_key).strip()


def normalize_market_dataframe(history: pd.DataFrame) -> pd.DataFrame:
    if history is None or history.empty:
        return pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS)

    dataframe = history.copy()

    for column in REQUIRED_MARKET_COLUMNS:
        if column not in dataframe.columns:
            if column == "Adjusted Close" and "Close" in dataframe.columns:
                dataframe[column] = dataframe["Close"]
            else:
                dataframe[column] = None

    dataframe["Date"] = pd.to_datetime(
        dataframe["Date"],
        errors="coerce",
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
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

    dataframe = dataframe.dropna(subset=["Date", "Close"])
    dataframe = dataframe.sort_values("Date")
    dataframe = dataframe.reset_index(drop=True)

    return dataframe[REQUIRED_MARKET_COLUMNS]


def apply_period_filter(history: pd.DataFrame, period: str = "6mo") -> pd.DataFrame:
    if history is None or history.empty:
        return pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS)

    limit = PERIOD_LIMITS.get(period)

    if limit is None:
        return history.reset_index(drop=True)

    return history.tail(limit).reset_index(drop=True)


def cached_rows_to_dataframe(cached_rows: list[Any]) -> pd.DataFrame:
    if not cached_rows:
        return pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS)

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
        return clean_provider_error_message(data["Information"])

    if "Note" in data:
        return clean_provider_error_message(data["Note"])

    if "Error Message" in data:
        return clean_provider_error_message(data["Error Message"])

    return None


def parse_alpha_vantage_daily_response(
    data: dict[str, Any],
    ticker: str,
) -> tuple[pd.DataFrame, str | None]:
    provider_error = parse_alpha_vantage_error(data)

    if provider_error:
        return pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS), provider_error

    time_series = data.get("Time Series (Daily)")

    if not time_series:
        return (
            pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS),
            "No market data found for " + ticker,
        )

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
        return (
            pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS),
            "No usable close price data found for " + ticker,
        )

    return history, None


def fetch_alpha_vantage_daily_data(
    ticker: object,
) -> tuple[pd.DataFrame, str | None]:
    clean_ticker = clean_ticker_symbol(ticker)

    is_valid_format, validation_result = is_valid_ticker_format(clean_ticker)

    if not is_valid_format:
        return pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS), validation_result

    api_key = get_alpha_vantage_key()

    if not api_key:
        return pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS), "Missing Alpha Vantage API key."

    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": clean_ticker,
        "outputsize": "compact",
        "apikey": api_key,
    }

    try:
        response = requests.get(
            BASE_URL,
            params=params,
            timeout=15,
        )

        response.raise_for_status()
        data = response.json()

        return parse_alpha_vantage_daily_response(data, clean_ticker)

    except requests.exceptions.Timeout:
        return (
            pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS),
            "Market data request timed out for " + clean_ticker,
        )

    except requests.exceptions.RequestException as error:
        return (
            pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS),
            "Market data request error for "
            + clean_ticker
            + ": "
            + str(error),
        )

    except ValueError:
        return (
            pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS),
            "Market data response was not valid JSON for " + clean_ticker,
        )

    except Exception as error:
        return (
            pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS),
            "Market data error for " + clean_ticker + ": " + str(error),
        )


def load_cached_stock_data(
    ticker: object,
    period: str = "6mo",
) -> tuple[pd.DataFrame, str | None]:
    clean_ticker = clean_ticker_symbol(ticker)

    try:
        cached_rows = get_cached_market_data(clean_ticker)
        cached_history = cached_rows_to_dataframe(cached_rows)

        if cached_history.empty:
            return pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS), "No cached market data."

        return apply_period_filter(cached_history, period), None

    except Exception as error:
        return (
            pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS),
            "Cache read error for " + clean_ticker + ": " + str(error),
        )


@st.cache_data(ttl=21600)
def get_stock_data(
    ticker: object,
    period: str = "6mo",
    force_refresh: bool = False,
    cache_only: bool = False,
) -> tuple[pd.DataFrame, str | None]:
    clean_ticker = clean_ticker_symbol(ticker)

    is_valid_format, validation_result = is_valid_ticker_format(clean_ticker)

    if not is_valid_format:
        return pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS), validation_result

    if not force_refresh:
        cached_history, cache_error = load_cached_stock_data(
            clean_ticker,
            period,
        )

        if not cached_history.empty:
            return cached_history, None

        if cache_only:
            message = (
                f"{clean_ticker} is not cached in Neon yet. "
                "Turn off cache-only mode after your API quota resets, "
                "or seed this ticker into market_data_cache."
            )

            return pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS), message

    if cache_only:
        message = (
            f"{clean_ticker} is not cached in Neon yet. "
            "Cache-only mode prevents Alpha Vantage requests."
        )

        return pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS), message

    fresh_history, fresh_error = fetch_alpha_vantage_daily_data(clean_ticker)

    if fresh_error:
        return pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS), fresh_error

    if fresh_history.empty:
        return (
            pd.DataFrame(columns=REQUIRED_MARKET_COLUMNS),
            "No market data found for " + clean_ticker,
        )

    save_market_data_cache(clean_ticker, fresh_history)

    filtered_history = apply_period_filter(
        fresh_history,
        period,
    )

    return filtered_history, None


def load_stock_data(
    ticker: object,
    period: str = "6mo",
    force_refresh: bool = False,
    cache_only: bool = False,
):
    history, error = get_stock_data(
        ticker,
        period,
        force_refresh=force_refresh,
        cache_only=cache_only,
    )

    info = {
        "ticker": clean_ticker_symbol(ticker),
        "source": "Neon Cache / Alpha Vantage",
    }

    if error:
        return info, history, error

    return info, history, None



@st.cache_data(ttl=21600)
def get_current_price(ticker: object) -> float | None:
    clean_ticker = clean_ticker_symbol(ticker)

    is_valid_format, _ = is_valid_ticker_format(clean_ticker)

    if not is_valid_format:
        return None

    cached_history, _ = load_cached_stock_data(
        clean_ticker,
        "6mo",
    )

    if not cached_history.empty:
        return float(cached_history["Close"].iloc[-1])

    history, error = get_stock_data(
        clean_ticker,
        "6mo",
        force_refresh=False,
    )

    if error or history.empty:
        return None

    return float(history["Close"].iloc[-1])


def get_latest_price(ticker: object) -> float | None:
    return get_current_price(ticker)


def calculate_price_change(history: pd.DataFrame) -> tuple[float, float]:
    if history is None or history.empty:
        return 0, 0

    if "Close" not in history.columns:
        return 0, 0

    close_prices = pd.to_numeric(
        history["Close"],
        errors="coerce",
    ).dropna()

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


def get_stock_volatility(ticker: object) -> float:
    clean_ticker = clean_ticker_symbol(ticker)

    history, error = get_stock_data(
        clean_ticker,
        "6mo",
        force_refresh=False,
    )

    if error or history.empty:
        return 0

    if "Close" not in history.columns:
        return 0

    close_prices = pd.to_numeric(
        history["Close"],
        errors="coerce",
    ).dropna()

    if close_prices.empty:
        return 0

    daily_returns = close_prices.pct_change().dropna()

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
