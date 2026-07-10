from __future__ import annotations

import pandas as pd

from core.sector_map import DEFAULT_SECTOR
from core.sector_map import TICKER_SECTOR_MAP


def get_position_weight_status(allocation_pct: float) -> tuple[str, str]:
    """Return position weight label and risk note."""
    if allocation_pct >= 50:
        return (
            "Concentrated risk",
            "This position is more than half of the portfolio.",
        )

    if allocation_pct >= 25:
        return (
            "Heavy position",
            "This position has meaningful concentration risk.",
        )

    if allocation_pct >= 10:
        return (
            "Moderate position",
            "This position is within a normal active range.",
        )

    return (
        "Small position",
        "This position has limited portfolio impact.",
    )


def build_position_weight_dataframe(portfolio_df: pd.DataFrame) -> pd.DataFrame:
    """Build position weight dataframe with status and risk notes."""
    if portfolio_df is None or portfolio_df.empty:
        return pd.DataFrame()

    required_columns = [
        "Ticker",
        "Current Value",
        "Allocation %",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in portfolio_df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Portfolio dataframe is missing required columns: "
            + ", ".join(missing_columns)
        )

    weight_df = portfolio_df[
        [
            "Ticker",
            "Current Value",
            "Allocation %",
        ]
    ].copy()

    weight_df = weight_df.sort_values(
        by="Allocation %",
        ascending=False,
    )

    status_rows = weight_df["Allocation %"].apply(
        lambda value: get_position_weight_status(float(value))
    )

    weight_df["Weight Status"] = status_rows.apply(lambda item: item[0])
    weight_df["Risk Note"] = status_rows.apply(lambda item: item[1])

    return weight_df


def build_sector_exposure_dataframe(portfolio_df: pd.DataFrame) -> pd.DataFrame:
    """Build sector exposure dataframe from portfolio current value."""
    if portfolio_df is None or portfolio_df.empty:
        return pd.DataFrame()

    required_columns = [
        "Ticker",
        "Current Value",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in portfolio_df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Portfolio dataframe is missing required columns: "
            + ", ".join(missing_columns)
        )

    sector_df = portfolio_df[
        [
            "Ticker",
            "Current Value",
        ]
    ].copy()

    sector_df["Sector"] = sector_df["Ticker"].map(
        lambda ticker: TICKER_SECTOR_MAP.get(
            str(ticker).upper(),
            DEFAULT_SECTOR,
        )
    )

    grouped_df = (
        sector_df.groupby("Sector", as_index=False)["Current Value"]
        .sum()
        .sort_values(by="Current Value", ascending=False)
    )

    total_value = float(grouped_df["Current Value"].sum())

    if total_value > 0:
        grouped_df["Exposure %"] = (
            grouped_df["Current Value"] / total_value
        ) * 100
    else:
        grouped_df["Exposure %"] = 0.0

    return grouped_df
