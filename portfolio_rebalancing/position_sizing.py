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


def validate_risk_budget_weights(
    risk_budget_weights: list[float],
    candidate_count: int,
) -> None:
    """Validate custom risk-budget weights."""
    if candidate_count <= 0:
        raise ValueError("candidate_count must be greater than zero")

    if len(risk_budget_weights) != candidate_count:
        raise ValueError("risk_budget_weights length must match candidate count")

    if any(weight < 0 for weight in risk_budget_weights):
        raise ValueError("risk_budget_weights cannot contain negative values")

    total_weight = sum(risk_budget_weights)

    if not 0.999 <= total_weight <= 1.001:
        raise ValueError("risk_budget_weights must sum to 1.0")


def calculate_equal_risk_budget_weights(candidate_count: int) -> list[float]:
    """Calculate equal risk-budget weights."""
    if candidate_count <= 0:
        raise ValueError("candidate_count must be greater than zero")

    return [1.0 / candidate_count] * candidate_count


def calculate_risk_budget_allocations(
    candidates: pd.DataFrame,
    total_risk_budget_pct: float,
    risk_budget_weights: list[float] | None = None,
) -> pd.DataFrame:
    """Calculate per-candidate risk budget allocation."""
    if candidates.empty:
        raise ValueError("candidates cannot be empty")

    if total_risk_budget_pct <= 0:
        raise ValueError("total_risk_budget_pct must be greater than zero")

    if "ticker" not in candidates.columns:
        raise ValueError("candidates missing required columns: ticker")

    candidate_count = len(candidates)

    if risk_budget_weights is None:
        risk_budget_weights = calculate_equal_risk_budget_weights(candidate_count)
    else:
        validate_risk_budget_weights(
            risk_budget_weights=risk_budget_weights,
            candidate_count=candidate_count,
        )

    result = candidates[["ticker"]].copy()
    result["ticker"] = result["ticker"].astype(str).str.strip().str.upper()
    result["risk_budget_weight"] = risk_budget_weights
    result["risk_budget_pct"] = result["risk_budget_weight"] * total_risk_budget_pct

    return result


def calculate_risk_budget_position_sizing_table(
    candidates: pd.DataFrame,
    portfolio_value: float,
    total_risk_budget_pct: float,
    stop_loss_pct: float,
    max_position_weight_pct: float = 100.0,
    allow_fractional_shares: bool = True,
    risk_budget_weights: list[float] | None = None,
) -> pd.DataFrame:
    """Calculate position sizing table using a shared portfolio risk budget."""
    required_columns = {"ticker", "current_price"}
    missing_columns = required_columns - set(candidates.columns)

    if candidates.empty:
        raise ValueError("candidates cannot be empty")

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"candidates missing required columns: {missing}")

    risk_budget_allocations = calculate_risk_budget_allocations(
        candidates=candidates,
        total_risk_budget_pct=total_risk_budget_pct,
        risk_budget_weights=risk_budget_weights,
    )

    merged_candidates = candidates.copy()
    merged_candidates["ticker"] = (
        merged_candidates["ticker"].astype(str).str.strip().str.upper()
    )

    merged_candidates = merged_candidates.merge(
        risk_budget_allocations,
        on="ticker",
        how="left",
    )

    rows = []

    for _, row in merged_candidates.iterrows():
        sizing = calculate_risk_based_position_size(
            portfolio_value=portfolio_value,
            risk_per_trade_pct=float(row["risk_budget_pct"]),
            stop_loss_pct=stop_loss_pct,
            current_price=float(row["current_price"]),
            max_position_weight_pct=max_position_weight_pct,
            allow_fractional_shares=allow_fractional_shares,
        )

        sizing["ticker"] = row["ticker"]
        sizing["risk_budget_weight"] = float(row["risk_budget_weight"])
        sizing["allocated_risk_budget_pct"] = float(row["risk_budget_pct"])
        sizing["allocated_risk_budget_amount"] = float(
            portfolio_value * (float(row["risk_budget_pct"]) / 100)
        )

        rows.append(sizing)

    result = pd.DataFrame(rows)

    ordered_columns = [
        "ticker",
        "current_price",
        "portfolio_value",
        "risk_budget_weight",
        "allocated_risk_budget_pct",
        "allocated_risk_budget_amount",
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


def build_risk_budget_position_sizing_summary(
    risk_budget_table: pd.DataFrame,
) -> dict[str, float | int]:
    """Build summary for risk-budget position sizing."""
    if risk_budget_table.empty:
        raise ValueError("risk_budget_table cannot be empty")

    return {
        "candidate_count": len(risk_budget_table),
        "total_allocated_risk_budget_pct": float(
            risk_budget_table["allocated_risk_budget_pct"].sum()
        ),
        "total_allocated_risk_budget_amount": float(
            risk_budget_table["allocated_risk_budget_amount"].sum()
        ),
        "total_estimated_dollar_risk": float(
            risk_budget_table["estimated_dollar_risk"].sum()
        ),
        "total_position_value": float(
            risk_budget_table["final_position_value"].sum()
        ),
        "average_position_weight_pct": float(
            risk_budget_table["final_position_weight_pct"].mean()
        ),
        "max_position_weight_pct": float(
            risk_budget_table["final_position_weight_pct"].max()
        ),
        "capped_position_count": int(
            risk_budget_table["capped_by_max_weight"].sum()
        ),
        "risk_sized_position_count": int(
            (risk_budget_table["sizing_status"] == "Risk Sized").sum()
        ),
    }
