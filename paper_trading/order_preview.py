from __future__ import annotations

from typing import Any

import pandas as pd

from paper_trading.models import OrderSide, OrderType
from paper_trading.order_ticket import (
    build_order_preview_table_row,
    build_order_ticket,
)


def calculate_position_after_order(
    side: OrderSide,
    current_position_quantity: float,
    order_quantity: float,
) -> float:
    """Calculate estimated position quantity after a buy or sell order."""
    if current_position_quantity < 0:
        raise ValueError("current_position_quantity cannot be negative")

    if order_quantity <= 0:
        raise ValueError("order_quantity must be greater than zero")

    if side == OrderSide.BUY:
        return float(current_position_quantity + order_quantity)

    if order_quantity > current_position_quantity:
        raise ValueError("sell quantity cannot exceed current position quantity")

    return float(current_position_quantity - order_quantity)


def calculate_position_value_after_order(
    position_quantity_after_order: float,
    estimated_price: float,
) -> float:
    """Calculate estimated position value after order."""
    if position_quantity_after_order < 0:
        raise ValueError("position_quantity_after_order cannot be negative")

    if estimated_price <= 0:
        raise ValueError("estimated_price must be greater than zero")

    return float(position_quantity_after_order * estimated_price)


def calculate_portfolio_exposure_pct(
    position_value: float,
    portfolio_value: float,
) -> float:
    """Calculate estimated position exposure as a percentage of portfolio value."""
    if position_value < 0:
        raise ValueError("position_value cannot be negative")

    if portfolio_value <= 0:
        raise ValueError("portfolio_value must be greater than zero")

    return float(position_value / portfolio_value * 100)


def classify_order_preview_status(
    is_valid: bool,
    exposure_pct_after_order: float,
    max_exposure_pct: float = 25.0,
) -> str:
    """Classify order preview status."""
    if max_exposure_pct <= 0:
        raise ValueError("max_exposure_pct must be greater than zero")

    if not is_valid:
        return "Rejected"

    if exposure_pct_after_order > max_exposure_pct:
        return "Warning"

    return "Accepted"


def build_order_preview_reason(
    side: OrderSide,
    preview_status: str,
    ticker: str,
    exposure_pct_after_order: float,
    max_exposure_pct: float,
    rejection_reason: str | None = None,
) -> str:
    """Build plain-English preview reason."""
    clean_ticker = ticker.strip().upper()

    if preview_status == "Rejected":
        return rejection_reason or f"{clean_ticker} order was rejected."

    if preview_status == "Warning":
        return (
            f"{clean_ticker} {side.value.lower()} order is valid, but estimated "
            f"exposure is {exposure_pct_after_order:.2f}%, above the "
            f"{max_exposure_pct:.2f}% max exposure rule."
        )

    return (
        f"{clean_ticker} {side.value.lower()} order is valid and within "
        f"the {max_exposure_pct:.2f}% max exposure rule."
    )


def build_buy_sell_order_preview(
    account_id: str,
    ticker: str,
    side: OrderSide,
    quantity: float,
    order_type: OrderType,
    estimated_price: float,
    cash_balance: float,
    portfolio_value: float,
    current_position_quantity: float = 0.0,
    limit_price: float | None = None,
    commission_rate_pct: float = 0.0,
    minimum_commission: float = 0.0,
    max_exposure_pct: float = 25.0,
) -> dict[str, Any]:
    """Build a complete buy/sell order preview."""
    if portfolio_value <= 0:
        raise ValueError("portfolio_value must be greater than zero")

    order_ticket = build_order_ticket(
        account_id=account_id,
        ticker=ticker,
        side=side,
        quantity=quantity,
        order_type=order_type,
        estimated_price=estimated_price,
        limit_price=limit_price,
        cash_balance=cash_balance,
        current_position_quantity=current_position_quantity,
        commission_rate_pct=commission_rate_pct,
        minimum_commission=minimum_commission,
    )

    if order_ticket["is_valid"]:
        position_quantity_after_order = calculate_position_after_order(
            side=side,
            current_position_quantity=current_position_quantity,
            order_quantity=quantity,
        )
    else:
        position_quantity_after_order = float(current_position_quantity)

    position_value_before_order = calculate_position_value_after_order(
        position_quantity_after_order=current_position_quantity,
        estimated_price=estimated_price,
    )

    position_value_after_order = calculate_position_value_after_order(
        position_quantity_after_order=position_quantity_after_order,
        estimated_price=estimated_price,
    )

    exposure_pct_before_order = calculate_portfolio_exposure_pct(
        position_value=position_value_before_order,
        portfolio_value=portfolio_value,
    )

    exposure_pct_after_order = calculate_portfolio_exposure_pct(
        position_value=position_value_after_order,
        portfolio_value=portfolio_value,
    )

    preview_status = classify_order_preview_status(
        is_valid=order_ticket["is_valid"],
        exposure_pct_after_order=exposure_pct_after_order,
        max_exposure_pct=max_exposure_pct,
    )

    preview_reason = build_order_preview_reason(
        side=side,
        preview_status=preview_status,
        ticker=ticker,
        exposure_pct_after_order=exposure_pct_after_order,
        max_exposure_pct=max_exposure_pct,
        rejection_reason=order_ticket["rejection_reason"],
    )

    preview = {
        **build_order_preview_table_row(order_ticket),
        "portfolio_value": float(portfolio_value),
        "current_position_quantity": float(current_position_quantity),
        "position_quantity_after_order": float(position_quantity_after_order),
        "position_value_before_order": float(position_value_before_order),
        "position_value_after_order": float(position_value_after_order),
        "exposure_pct_before_order": float(exposure_pct_before_order),
        "exposure_pct_after_order": float(exposure_pct_after_order),
        "max_exposure_pct": float(max_exposure_pct),
        "preview_status": preview_status,
        "preview_reason": preview_reason,
    }

    return preview


def build_order_preview_dataframe(previews: list[dict[str, Any]]) -> pd.DataFrame:
    """Build a table-ready DataFrame from order previews."""
    if not previews:
        raise ValueError("previews cannot be empty")

    return pd.DataFrame(previews)


def build_order_preview_summary(previews: list[dict[str, Any]]) -> dict[str, float | int]:
    """Build summary metrics for multiple order previews."""
    if not previews:
        raise ValueError("previews cannot be empty")

    preview_df = build_order_preview_dataframe(previews)

    return {
        "preview_count": len(preview_df),
        "accepted_count": int((preview_df["preview_status"] == "Accepted").sum()),
        "warning_count": int((preview_df["preview_status"] == "Warning").sum()),
        "rejected_count": int((preview_df["preview_status"] == "Rejected").sum()),
        "buy_count": int((preview_df["side"] == "Buy").sum()),
        "sell_count": int((preview_df["side"] == "Sell").sum()),
        "total_estimated_order_value": float(
            preview_df["estimated_order_value"].sum()
        ),
        "total_estimated_commission": float(
            preview_df["estimated_commission"].sum()
        ),
        "total_estimated_cash_impact": float(
            preview_df["estimated_cash_impact"].sum()
        ),
        "max_exposure_pct_after_order": float(
            preview_df["exposure_pct_after_order"].max()
        ),
    }
