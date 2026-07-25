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


def classify_allocation_drift(
    drift_weight_pct: float,
    rebalance_threshold_pct: float = 5.0,
) -> str:
    """Classify allocation drift severity."""
    absolute_drift = abs(float(drift_weight_pct))

    if absolute_drift >= rebalance_threshold_pct:
        return "Rebalance Needed"

    if absolute_drift >= rebalance_threshold_pct / 2:
        return "Watch"

    return "On Target"


def calculate_target_vs_current_allocations(
    positions: pd.DataFrame,
    rebalance_threshold_pct: float = 5.0,
) -> pd.DataFrame:
    """Compare current allocation against target allocation."""
    if rebalance_threshold_pct <= 0:
        raise ValueError("rebalance_threshold_pct must be greater than zero")

    weighted_positions = calculate_current_weights(positions)

    result = weighted_positions.copy()
    result["allocation_drift_pct"] = (
        result["current_weight_pct"] - result["target_weight_pct"]
    )
    result["absolute_drift_pct"] = result["allocation_drift_pct"].abs()
    result["drift_status"] = result["allocation_drift_pct"].apply(
        lambda drift: classify_allocation_drift(
            drift_weight_pct=drift,
            rebalance_threshold_pct=rebalance_threshold_pct,
        )
    )
    result["needs_rebalance"] = (
        result["absolute_drift_pct"] >= rebalance_threshold_pct
    )

    ordered_columns = [
        "ticker",
        "shares",
        "current_price",
        "current_value",
        "current_weight",
        "current_weight_pct",
        "target_weight",
        "target_weight_pct",
        "allocation_drift_pct",
        "absolute_drift_pct",
        "drift_status",
        "needs_rebalance",
    ]

    return result[ordered_columns]


def build_allocation_drift_summary(
    positions: pd.DataFrame,
    rebalance_threshold_pct: float = 5.0,
) -> dict[str, float | int]:
    """Build summary metrics for target-vs-current allocation drift."""
    allocation_view = calculate_target_vs_current_allocations(
        positions=positions,
        rebalance_threshold_pct=rebalance_threshold_pct,
    )

    return {
        "position_count": len(allocation_view),
        "rebalance_threshold_pct": rebalance_threshold_pct,
        "positions_needing_rebalance": int(
            allocation_view["needs_rebalance"].sum()
        ),
        "positions_on_watch": int(
            (allocation_view["drift_status"] == "Watch").sum()
        ),
        "positions_on_target": int(
            (allocation_view["drift_status"] == "On Target").sum()
        ),
        "max_absolute_drift_pct": float(
            allocation_view["absolute_drift_pct"].max()
        ),
        "average_absolute_drift_pct": float(
            allocation_view["absolute_drift_pct"].mean()
        ),
        "total_absolute_drift_pct": float(
            allocation_view["absolute_drift_pct"].sum()
        ),
    }


def classify_trade_priority(
    absolute_trade_value: float,
    total_portfolio_value: float,
    high_priority_pct: float = 10.0,
    medium_priority_pct: float = 5.0,
) -> str:
    """Classify trade priority based on trade size relative to portfolio value."""
    if total_portfolio_value <= 0:
        raise ValueError("total_portfolio_value must be greater than zero")

    trade_pct = abs(float(absolute_trade_value)) / total_portfolio_value * 100

    if trade_pct >= high_priority_pct:
        return "High"

    if trade_pct >= medium_priority_pct:
        return "Medium"

    if trade_pct > 0:
        return "Low"

    return "None"


def build_trade_reason(action: str, drift_weight_pct: float) -> str:
    """Build plain-English reason for a rebalance trade."""
    if action == "Buy":
        return f"Position is under target by {abs(drift_weight_pct):.2f}%."

    if action == "Sell":
        return f"Position is over target by {abs(drift_weight_pct):.2f}%."

    return "Position is close enough to target allocation."


def calculate_dollar_trade_recommendations(
    positions: pd.DataFrame,
    trade_tolerance: float = 1.0,
) -> pd.DataFrame:
    """Calculate dollar buy/sell recommendations from rebalance plan."""
    if trade_tolerance < 0:
        raise ValueError("trade_tolerance cannot be negative")

    plan = calculate_rebalance_plan(positions)
    total_portfolio_value = float(plan["current_value"].sum())

    result = plan.copy()
    result["buy_amount"] = result["trade_value"].clip(lower=0.0)
    result["sell_amount"] = result["trade_value"].clip(upper=0.0).abs()
    result["absolute_trade_value"] = result["trade_value"].abs()

    result["trade_direction"] = result["trade_value"].apply(
        lambda value: classify_trade_action(
            trade_value=value,
            tolerance=trade_tolerance,
        )
    )

    result["trade_priority"] = result["absolute_trade_value"].apply(
        lambda value: classify_trade_priority(
            absolute_trade_value=value,
            total_portfolio_value=total_portfolio_value,
        )
    )

    result["trade_reason"] = result.apply(
        lambda row: build_trade_reason(
            action=row["trade_direction"],
            drift_weight_pct=row["drift_weight_pct"],
        ),
        axis=1,
    )

    ordered_columns = [
        "ticker",
        "current_value",
        "target_value",
        "current_weight_pct",
        "target_weight_pct",
        "drift_weight_pct",
        "trade_value",
        "buy_amount",
        "sell_amount",
        "absolute_trade_value",
        "trade_direction",
        "trade_priority",
        "trade_reason",
    ]

    return result[ordered_columns]


def build_dollar_trade_summary(
    positions: pd.DataFrame,
    trade_tolerance: float = 1.0,
) -> dict[str, float | int]:
    """Build summary of dollar trade recommendations."""
    recommendations = calculate_dollar_trade_recommendations(
        positions=positions,
        trade_tolerance=trade_tolerance,
    )

    total_buy_amount = float(recommendations["buy_amount"].sum())
    total_sell_amount = float(recommendations["sell_amount"].sum())
    gross_trade_amount = float(recommendations["absolute_trade_value"].sum())
    net_trade_amount = float(recommendations["trade_value"].sum())

    return {
        "recommendation_count": len(recommendations),
        "buy_recommendations": int(
            (recommendations["trade_direction"] == "Buy").sum()
        ),
        "sell_recommendations": int(
            (recommendations["trade_direction"] == "Sell").sum()
        ),
        "hold_recommendations": int(
            (recommendations["trade_direction"] == "Hold").sum()
        ),
        "high_priority_trades": int(
            (recommendations["trade_priority"] == "High").sum()
        ),
        "medium_priority_trades": int(
            (recommendations["trade_priority"] == "Medium").sum()
        ),
        "low_priority_trades": int(
            (recommendations["trade_priority"] == "Low").sum()
        ),
        "total_buy_amount": total_buy_amount,
        "total_sell_amount": total_sell_amount,
        "gross_trade_amount": gross_trade_amount,
        "net_trade_amount": net_trade_amount,
    }
