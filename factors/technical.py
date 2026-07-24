from __future__ import annotations

import pandas as pd


REQUIRED_PRICE_COLUMNS = {"Date", "Open", "High", "Low", "Close", "Volume"}


def validate_price_data(price_data: pd.DataFrame) -> None:
    """Validate standardized OHLCV price data."""
    missing_columns = REQUIRED_PRICE_COLUMNS - set(price_data.columns)

    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    if price_data.empty:
        raise ValueError("price_data cannot be empty")

    if price_data["Close"].isna().any():
        raise ValueError("Close column cannot contain missing values")

    if (price_data["Close"] <= 0).any():
        raise ValueError("Close column must contain positive prices")


def add_returns(price_data: pd.DataFrame) -> pd.DataFrame:
    """Add daily and cumulative return factors."""
    validate_price_data(price_data)

    factors = price_data.copy()
    factors["daily_return"] = factors["Close"].pct_change().fillna(0.0)
    factors["cumulative_return"] = (1 + factors["daily_return"]).cumprod() - 1

    return factors


def add_moving_averages(
    price_data: pd.DataFrame,
    windows: tuple[int, ...] = (20, 50, 200),
) -> pd.DataFrame:
    """Add simple moving average factors."""
    validate_price_data(price_data)

    factors = price_data.copy()

    for window in windows:
        if window <= 0:
            raise ValueError("moving average windows must be greater than 0")

        factors[f"ma_{window}"] = (
            factors["Close"]
            .rolling(window=window, min_periods=1)
            .mean()
        )

    return factors


def add_volatility(
    price_data: pd.DataFrame,
    window: int = 20,
    annualization_factor: int = 252,
) -> pd.DataFrame:
    """Add rolling annualized volatility factor."""
    validate_price_data(price_data)

    if window <= 0:
        raise ValueError("window must be greater than 0")

    factors = add_returns(price_data)
    factors[f"volatility_{window}"] = (
        factors["daily_return"]
        .rolling(window=window, min_periods=2)
        .std()
        .fillna(0.0)
        * (annualization_factor ** 0.5)
    )

    return factors


def add_momentum(
    price_data: pd.DataFrame,
    window: int = 20,
) -> pd.DataFrame:
    """Add price momentum factor."""
    validate_price_data(price_data)

    if window <= 0:
        raise ValueError("window must be greater than 0")

    factors = price_data.copy()
    factors[f"momentum_{window}"] = factors["Close"].pct_change(periods=window).fillna(0.0)

    return factors


def add_rsi(
    price_data: pd.DataFrame,
    window: int = 14,
) -> pd.DataFrame:
    """Add Relative Strength Index factor."""
    validate_price_data(price_data)

    if window <= 0:
        raise ValueError("window must be greater than 0")

    factors = price_data.copy()

    delta = factors["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    average_gain = gain.rolling(window=window, min_periods=window).mean()
    average_loss = loss.rolling(window=window, min_periods=window).mean()

    relative_strength = average_gain / average_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + relative_strength))

    factors[f"rsi_{window}"] = rsi.fillna(50.0)

    return factors


def add_macd(
    price_data: pd.DataFrame,
    fast_window: int = 12,
    slow_window: int = 26,
    signal_window: int = 9,
) -> pd.DataFrame:
    """Add MACD, MACD signal, and MACD histogram factors."""
    validate_price_data(price_data)

    if fast_window <= 0 or slow_window <= 0 or signal_window <= 0:
        raise ValueError("MACD windows must be greater than 0")

    if fast_window >= slow_window:
        raise ValueError("fast_window must be less than slow_window")

    factors = price_data.copy()

    fast_ema = factors["Close"].ewm(span=fast_window, adjust=False).mean()
    slow_ema = factors["Close"].ewm(span=slow_window, adjust=False).mean()

    factors["macd"] = fast_ema - slow_ema
    factors["macd_signal"] = factors["macd"].ewm(
        span=signal_window,
        adjust=False,
    ).mean()
    factors["macd_histogram"] = factors["macd"] - factors["macd_signal"]

    return factors


def add_volume_average(
    price_data: pd.DataFrame,
    window: int = 20,
) -> pd.DataFrame:
    """Add rolling average volume factor."""
    validate_price_data(price_data)

    if window <= 0:
        raise ValueError("window must be greater than 0")

    factors = price_data.copy()
    factors[f"volume_average_{window}"] = (
        factors["Volume"]
        .rolling(window=window, min_periods=1)
        .mean()
    )

    return factors


def add_price_distance_from_ma(
    price_data: pd.DataFrame,
    window: int = 50,
) -> pd.DataFrame:
    """Add percentage distance between close price and moving average."""
    validate_price_data(price_data)

    if window <= 0:
        raise ValueError("window must be greater than 0")

    factors = add_moving_averages(price_data, windows=(window,))
    ma_column = f"ma_{window}"
    distance_column = f"price_distance_from_ma_{window}"

    factors[distance_column] = (
        (factors["Close"] - factors[ma_column]) / factors[ma_column]
    ) * 100

    return factors


def build_technical_factor_table(price_data: pd.DataFrame) -> pd.DataFrame:
    """Build a standard technical factor table for research and strategy use."""
    validate_price_data(price_data)

    factors = price_data.copy()

    factors = add_returns(factors)
    factors = add_moving_averages(factors, windows=(20, 50, 200))
    factors = add_volatility(factors, window=20)
    factors = add_momentum(factors, window=20)
    factors = add_rsi(factors, window=14)
    factors = add_macd(factors)
    factors = add_volume_average(factors, window=20)
    factors = add_price_distance_from_ma(factors, window=50)

    return factors
