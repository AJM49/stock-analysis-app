from __future__ import annotations

import pandas as pd


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
