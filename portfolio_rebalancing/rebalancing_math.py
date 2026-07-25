from __future__ import annotations

import pandas as pd


REQUIRED_POSITION_COLUMNS = {
    "ticker",
    "shares",
    "current_price",
    "target_weight",
}


def validate_positions_frame(positions: pd.DataFrame) -> None:
    """Validate portfolio positions for rebalancing calculations."""
    if positions.empty:
        raise ValueError("positions cannot be empty")

    missing_columns = REQUIRED_POSITION_COLUMNS - set(positions.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"positions missing required columns: {missing}")

    if positions["ticker"].isna().any():
        raise ValueError("ticker cannot contain missing values")

    if (positions["shares"] < 0).any():
        raise ValueError("shares cannot contain negative values")

    if (positions["current_price"] <= 0).any():
        raise ValueError("current_price must be greater than zero")

    if (positions["target_weight"] < 0).any():
        raise ValueError("target_weight cannot contain negative values")

    target_weight_sum = float(positions["target_weight"].sum())

    if not 0.999 <= target_weight_sum <= 1.001:
        raise ValueError("target_weight must sum to 1.0")


def calculate_current_values(positions: pd.DataFrame) -> pd.DataFrame:
    """Calculate current market value for each position."""
    validate_positions_frame(positions)

    result = positions.copy()
    result["ticker"] = result["ticker"].astype(str).str.strip().str.upper()
    result["current_value"] = result["shares"] * result["current_price"]

    return result


def calculate_total_portfolio_value(positions: pd.DataFrame) -> float:
    """Calculate total portfolio market value."""
    valued_positions = calculate_current_values(positions)

    return float(valued_positions["current_value"].sum())


def calculate_current_weights(positions: pd.DataFrame) -> pd.DataFrame:
    """Calculate current allocation weights."""
    result = calculate_current_values(positions)
    total_value = float(result["current_value"].sum())

    if total_value <= 0:
        raise ValueError("total portfolio value must be greater than zero")

    result["current_weight"] = result["current_value"] / total_value
    result["current_weight_pct"] = result["current_weight"] * 100
    result["target_weight_pct"] = result["target_weight"] * 100

    return result


def calculate_rebalance_plan(positions: pd.DataFrame) -> pd.DataFrame:
    """Calculate target values, drift, and dollar trade recommendations."""
    result = calculate_current_weights(positions)
    total_value = float(result["current_value"].sum())

    result["target_value"] = result["target_weight"] * total_value
    result["drift_weight"] = result["current_weight"] - result["target_weight"]
    result["drift_weight_pct"] = result["drift_weight"] * 100
    result["trade_value"] = result["target_value"] - result["current_value"]

    result["action"] = result["trade_value"].apply(classify_trade_action)

    ordered_columns = [
        "ticker",
        "shares",
        "current_price",
        "current_value",
        "current_weight",
        "current_weight_pct",
        "target_weight",
        "target_weight_pct",
        "target_value",
        "drift_weight",
        "drift_weight_pct",
        "trade_value",
        "action",
    ]

    return result[ordered_columns]


def classify_trade_action(trade_value: float, tolerance: float = 1.0) -> str:
    """Classify trade action from target dollar trade value."""
    if trade_value > tolerance:
        return "Buy"

    if trade_value < -tolerance:
        return "Sell"

    return "Hold"


def build_rebalance_summary(positions: pd.DataFrame) -> dict[str, float | int]:
    """Build high-level rebalance summary metrics."""
    plan = calculate_rebalance_plan(positions)

    buy_count = int((plan["action"] == "Buy").sum())
    sell_count = int((plan["action"] == "Sell").sum())
    hold_count = int((plan["action"] == "Hold").sum())

    total_buy_value = float(plan.loc[plan["trade_value"] > 0, "trade_value"].sum())
    total_sell_value = float(abs(plan.loc[plan["trade_value"] < 0, "trade_value"].sum()))

    max_absolute_drift_pct = float(plan["drift_weight_pct"].abs().max())
    total_absolute_drift_pct = float(plan["drift_weight_pct"].abs().sum())

    return {
        "position_count": len(plan),
        "total_portfolio_value": float(plan["current_value"].sum()),
        "buy_count": buy_count,
        "sell_count": sell_count,
        "hold_count": hold_count,
        "total_buy_value": total_buy_value,
        "total_sell_value": total_sell_value,
        "max_absolute_drift_pct": max_absolute_drift_pct,
        "total_absolute_drift_pct": total_absolute_drift_pct,
    }
