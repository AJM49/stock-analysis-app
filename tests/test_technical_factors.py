from __future__ import annotations

import pandas as pd

from factors.technical import (
    add_macd,
    add_moving_averages,
    add_returns,
    add_rsi,
    build_technical_factor_table,
)


def build_sample_price_data() -> pd.DataFrame:
    """Create simple standardized test price data."""
    return pd.DataFrame(
        {
            "Date": pd.date_range("2026-01-01", periods=100, freq="D"),
            "Open": [100 + i for i in range(100)],
            "High": [101 + i for i in range(100)],
            "Low": [99 + i for i in range(100)],
            "Close": [100 + i for i in range(100)],
            "Volume": [1_000_000 + i for i in range(100)],
        }
    )


def test_add_returns_adds_expected_columns() -> None:
    price_data = build_sample_price_data()
    result = add_returns(price_data)

    assert "daily_return" in result.columns
    assert "cumulative_return" in result.columns
    assert len(result) == len(price_data)


def test_add_moving_averages_adds_expected_columns() -> None:
    price_data = build_sample_price_data()
    result = add_moving_averages(price_data, windows=(5, 20))

    assert "ma_5" in result.columns
    assert "ma_20" in result.columns
    assert len(result) == len(price_data)


def test_add_rsi_adds_expected_column() -> None:
    price_data = build_sample_price_data()
    result = add_rsi(price_data, window=14)

    assert "rsi_14" in result.columns
    assert result["rsi_14"].notna().all()


def test_add_macd_adds_expected_columns() -> None:
    price_data = build_sample_price_data()
    result = add_macd(price_data)

    assert "macd" in result.columns
    assert "macd_signal" in result.columns
    assert "macd_histogram" in result.columns


def test_build_technical_factor_table_adds_standard_factor_columns() -> None:
    price_data = build_sample_price_data()
    result = build_technical_factor_table(price_data)

    expected_columns = {
        "daily_return",
        "cumulative_return",
        "ma_20",
        "ma_50",
        "ma_200",
        "volatility_20",
        "momentum_20",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_histogram",
        "volume_average_20",
        "price_distance_from_ma_50",
    }

    assert expected_columns.issubset(result.columns)
    assert len(result) == len(price_data)
