from __future__ import annotations

import pandas as pd


def validate_position_sizing_inputs(
    portfolio_value: float,
    risk_per_trade_pct: float,
    stop_loss_pct: float,
    current_price: float,
    max_position_weight_pct: float = 100.0,
) -> None:
    """Validate inputs for position sizing calculations."""
    if portfolio_value <= 0:
        raise ValueError("portfolio_value must be greater than zero")

    if risk_per_trade_pct <= 0:
        raise ValueError("risk_per_trade_pct must be greater than zero")

    if stop_loss_pct <= 0:
        raise ValueError("stop_loss_pct must be greater than zero")

    if current_price <= 0:
        raise ValueError("current_price must be greater than zero")

    if max_position_weight_pct <= 0:
        raise ValueError("max_position_weight_pct must be greater than zero")

    if max_position_weight_pct > 100:
        raise ValueError("max_position_weight_pct cannot be greater than 100")


def calculate_risk_budget_amount(
    portfolio_value: float,
    risk_per_trade_pct: float,
) -> float:
    """Calculate dollar risk budget for a single trade."""
    if portfolio_value <= 0:
        raise ValueError("portfolio_value must be greater than zero")

    if risk_per_trade_pct <= 0:
        raise ValueError("risk_per_trade_pct must be greater than zero")

    return float(portfolio_value * (risk_per_trade_pct / 100))


def calculate_stop_loss_dollar_amount(
    current_price: float,
    stop_loss_pct: float,
) -> float:
    """Calculate dollar loss per share at the selected stop-loss percentage."""
    if current_price <= 0:
        raise ValueError("current_price must be greater than zero")

    if stop_loss_pct <= 0:
        raise ValueError("stop_loss_pct must be greater than zero")

    return float(current_price * (stop_loss_pct / 100))


def calculate_position_value_cap(
    portfolio_value: float,
    max_position_weight_pct: float,
) -> float:
    """Calculate maximum allowed dollar position size from allocation cap."""
    if portfolio_value <= 0:
        raise ValueError("portfolio_value must be greater than zero")

    if max_position_weight_pct <= 0:
        raise ValueError("max_position_weight_pct must be greater than zero")

    if max_position_weight_pct > 100:
        raise ValueError("max_position_weight_pct cannot be greater than 100")

    return float(portfolio_value * (max_position_weight_pct / 100))


def calculate_risk_based_position_size(
    portfolio_value: float,
    risk_per_trade_pct: float,
    stop_loss_pct: float,
    current_price: float,
    max_position_weight_pct: float = 100.0,
    allow_fractional_shares: bool = True,
) -> dict[str, float | bool | str]:
    """Calculate position size using risk budget and stop-loss distance."""
    validate_position_sizing_inputs(
        portfolio_value=portfolio_value,
        risk_per_trade_pct=risk_per_trade_pct,
        stop_loss_pct=stop_loss_pct,
        current_price=current_price,
        max_position_weight_pct=max_position_weight_pct,
    )

    risk_budget_amount = calculate_risk_budget_amount(
        portfolio_value=portfolio_value,
        risk_per_trade_pct=risk_per_trade_pct,
    )

    stop_loss_dollar_amount = calculate_stop_loss_dollar_amount(
        current_price=current_price,
        stop_loss_pct=stop_loss_pct,
    )

    raw_share_quantity = risk_budget_amount / stop_loss_dollar_amount

    if allow_fractional_shares:
        risk_based_share_quantity = raw_share_quantity
    else:
        risk_based_share_quantity = float(int(raw_share_quantity))

    risk_based_position_value = risk_based_share_quantity * current_price

    position_value_cap = calculate_position_value_cap(
        portfolio_value=portfolio_value,
        max_position_weight_pct=max_position_weight_pct,
    )

    cap_share_quantity = position_value_cap / current_price

    if not allow_fractional_shares:
        cap_share_quantity = float(int(cap_share_quantity))

    if risk_based_position_value > position_value_cap:
        final_share_quantity = cap_share_quantity
        capped_by_max_weight = True
    else:
        final_share_quantity = risk_based_share_quantity
        capped_by_max_weight = False

    final_position_value = final_share_quantity * current_price
    final_position_weight_pct = final_position_value / portfolio_value * 100
    estimated_dollar_risk = final_share_quantity * stop_loss_dollar_amount
    estimated_risk_pct = estimated_dollar_risk / portfolio_value * 100

    if final_share_quantity <= 0:
        sizing_status = "No Position"
    elif capped_by_max_weight:
        sizing_status = "Capped"
    else:
        sizing_status = "Risk Sized"

    return {
        "portfolio_value": float(portfolio_value),
        "risk_per_trade_pct": float(risk_per_trade_pct),
        "stop_loss_pct": float(stop_loss_pct),
        "current_price": float(current_price),
        "max_position_weight_pct": float(max_position_weight_pct),
        "allow_fractional_shares": allow_fractional_shares,
        "risk_budget_amount": float(risk_budget_amount),
        "stop_loss_dollar_amount": float(stop_loss_dollar_amount),
        "risk_based_share_quantity": float(risk_based_share_quantity),
        "position_value_cap": float(position_value_cap),
        "cap_share_quantity": float(cap_share_quantity),
        "final_share_quantity": float(final_share_quantity),
        "final_position_value": float(final_position_value),
        "final_position_weight_pct": float(final_position_weight_pct),
        "estimated_dollar_risk": float(estimated_dollar_risk),
        "estimated_risk_pct": float(estimated_risk_pct),
        "capped_by_max_weight": capped_by_max_weight,
        "sizing_status": sizing_status,
    }


def calculate_position_sizing_table(
    candidates: pd.DataFrame,
    portfolio_value: float,
    risk_per_trade_pct: float,
    stop_loss_pct: float,
    max_position_weight_pct: float = 100.0,
    allow_fractional_shares: bool = True,
) -> pd.DataFrame:
    """Calculate position sizing table for multiple candidate tickers."""
    required_columns = {"ticker", "current_price"}
    missing_columns = required_columns - set(candidates.columns)

    if candidates.empty:
        raise ValueError("candidates cannot be empty")

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"candidates missing required columns: {missing}")

    rows = []

    for _, row in candidates.iterrows():
        ticker = str(row["ticker"]).strip().upper()
        current_price = float(row["current_price"])

        sizing = calculate_risk_based_position_size(
            portfolio_value=portfolio_value,
            risk_per_trade_pct=risk_per_trade_pct,
            stop_loss_pct=stop_loss_pct,
            current_price=current_price,
            max_position_weight_pct=max_position_weight_pct,
            allow_fractional_shares=allow_fractional_shares,
        )

        sizing["ticker"] = ticker
        rows.append(sizing)

    result = pd.DataFrame(rows)

    ordered_columns = [
        "ticker",
        "current_price",
        "portfolio_value",
        "risk_per_trade_pct",
        "stop_loss_pct",
        "max_position_weight_pct",
        "risk_budget_amount",
        "stop_loss_dollar_amount",
        "final_share_quantity",
        "final_position_value",
        "final_position_weight_pct",
        "estimated_dollar_risk",
        "estimated_risk_pct",
        "capped_by_max_weight",
        "sizing_status",
    ]

    return result[ordered_columns]


def build_position_sizing_summary(position_sizing_table: pd.DataFrame) -> dict[str, float | int]:
    """Build high-level summary for a position sizing table."""
    if position_sizing_table.empty:
        raise ValueError("position_sizing_table cannot be empty")

    return {
        "candidate_count": len(position_sizing_table),
        "total_position_value": float(
            position_sizing_table["final_position_value"].sum()
        ),
        "total_estimated_dollar_risk": float(
            position_sizing_table["estimated_dollar_risk"].sum()
        ),
        "average_position_weight_pct": float(
            position_sizing_table["final_position_weight_pct"].mean()
        ),
        "max_position_weight_pct": float(
            position_sizing_table["final_position_weight_pct"].max()
        ),
        "capped_position_count": int(
            position_sizing_table["capped_by_max_weight"].sum()
        ),
        "risk_sized_position_count": int(
            (position_sizing_table["sizing_status"] == "Risk Sized").sum()
        ),
    }
