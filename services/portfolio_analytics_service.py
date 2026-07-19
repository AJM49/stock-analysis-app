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


def build_portfolio_risk_flags(
    portfolio_df: pd.DataFrame,
    sector_df: pd.DataFrame | None = None,
) -> list[dict]:
    """Build portfolio-level risk flags."""
    risk_flags = []

    if portfolio_df is None or portfolio_df.empty:
        return risk_flags

    if "Allocation %" in portfolio_df.columns:
        largest_position = portfolio_df.sort_values(
            by="Allocation %",
            ascending=False,
        ).iloc[0]

        largest_allocation = float(largest_position["Allocation %"])

        if largest_allocation >= 50:
            risk_flags.append(
                {
                    "Risk": "Single-position concentration",
                    "Level": "High",
                    "Detail": (
                        str(largest_position["Ticker"])
                        + " is more than 50% of the portfolio."
                    ),
                }
            )
        elif largest_allocation >= 25:
            risk_flags.append(
                {
                    "Risk": "Single-position concentration",
                    "Level": "Medium",
                    "Detail": (
                        str(largest_position["Ticker"])
                        + " is above 25% of the portfolio."
                    ),
                }
            )

    if "Price Status" in portfolio_df.columns:
        missing_price_df = portfolio_df[
            portfolio_df["Price Status"] == "Missing"
        ]

        if not missing_price_df.empty:
            risk_flags.append(
                {
                    "Risk": "Missing price data",
                    "Level": "Medium",
                    "Detail": (
                        str(len(missing_price_df))
                        + " position(s) are missing current market prices."
                    ),
                }
            )

    if "Gain/Loss %" in portfolio_df.columns:
        negative_df = portfolio_df[
            portfolio_df["Gain/Loss %"] < 0
        ]

        if not negative_df.empty:
            risk_flags.append(
                {
                    "Risk": "Negative unrealized return",
                    "Level": "Info",
                    "Detail": (
                        str(len(negative_df))
                        + " position(s) currently show unrealized losses."
                    ),
                }
            )

    if sector_df is not None and not sector_df.empty:
        largest_sector = sector_df.sort_values(
            by="Exposure %",
            ascending=False,
        ).iloc[0]

        largest_sector_exposure = float(largest_sector["Exposure %"])

        if largest_sector_exposure >= 50:
            risk_flags.append(
                {
                    "Risk": "Sector concentration",
                    "Level": "High",
                    "Detail": (
                        str(largest_sector["Sector"])
                        + " is more than 50% of the portfolio."
                    ),
                }
            )
        elif largest_sector_exposure >= 35:
            risk_flags.append(
                {
                    "Risk": "Sector concentration",
                    "Level": "Medium",
                    "Detail": (
                        str(largest_sector["Sector"])
                        + " is above 35% of the portfolio."
                    ),
                }
            )

    return risk_flags


def calculate_portfolio_risk_score(portfolio_df: pd.DataFrame) -> tuple[int, str, list[str]]:
    """Calculate portfolio risk score, level, and notes."""
    if portfolio_df is None or portfolio_df.empty:
        return 0, "No Data", ["No portfolio positions available."]

    score = 0
    notes = []

    if "Allocation %" in portfolio_df.columns and "Ticker" in portfolio_df.columns:
        largest_position = portfolio_df.sort_values(
            by="Allocation %",
            ascending=False,
        ).iloc[0]

        ticker = str(largest_position["Ticker"])
        allocation_pct = float(largest_position["Allocation %"])

        if allocation_pct >= 50:
            score += 35
            notes.append(f"{ticker} position concentration is {allocation_pct:.2f}%.")
        elif allocation_pct >= 25:
            score += 20
            notes.append(f"{ticker} position concentration is {allocation_pct:.2f}%.")

    try:
        sector_df = build_sector_exposure_dataframe(portfolio_df)
    except Exception:
        sector_df = pd.DataFrame()

    if sector_df is not None and not sector_df.empty:
        if "Sector" in sector_df.columns and "Exposure %" in sector_df.columns:
            largest_sector = sector_df.sort_values(
                by="Exposure %",
                ascending=False,
            ).iloc[0]

            sector = str(largest_sector["Sector"])
            exposure_pct = float(largest_sector["Exposure %"])

            if exposure_pct >= 50:
                score += 30
                notes.append(f"{sector} sector concentration is {exposure_pct:.2f}%.")
            elif exposure_pct >= 35:
                score += 15
                notes.append(f"{sector} sector concentration is {exposure_pct:.2f}%.")

    if "Price Status" in portfolio_df.columns:
        missing_price_count = int(
            (portfolio_df["Price Status"] == "Missing").sum()
        )

        if missing_price_count > 0:
            score += min(20, missing_price_count * 5)
            notes.append(f"{missing_price_count} position(s) have missing price data.")

    if "Gain/Loss" in portfolio_df.columns:
        total_gain_loss = float(portfolio_df["Gain/Loss"].sum())

        if total_gain_loss < 0:
            score += 15
            notes.append(
                f"Portfolio gain/loss is negative by ${total_gain_loss:,.2f}."
            )

    score = min(score, 100)

    if score >= 75:
        risk_level = "High Risk"
    elif score >= 50:
        risk_level = "Elevated Risk"
    elif score >= 25:
        risk_level = "Moderate Risk"
    else:
        risk_level = "Low Risk"

    if not notes:
        notes.append("No major risk triggers detected.")

    return score, risk_level, notes
