from __future__ import annotations

from dataclasses import asdict
from typing import Any

from paper_trading.models import (
    OrderSide,
    OrderType,
    PaperOrder,
    create_limit_order,
    create_market_order,
)


def validate_order_ticket_inputs(
    account_id: str,
    ticker: str,
    side: OrderSide,
    quantity: float,
    order_type: OrderType,
    estimated_price: float,
    limit_price: float | None = None,
    cash_balance: float | None = None,
    current_position_quantity: float | None = None,
    commission: float = 0.0,
) -> None:
    """Validate simulated order ticket inputs."""
    if not account_id:
        raise ValueError("account_id cannot be empty")

    if not ticker or not ticker.strip():
        raise ValueError("ticker cannot be empty")

    if quantity <= 0:
        raise ValueError("quantity must be greater than zero")

    if estimated_price <= 0:
        raise ValueError("estimated_price must be greater than zero")

    if commission < 0:
        raise ValueError("commission cannot be negative")

    if order_type == OrderType.LIMIT:
        if limit_price is None:
            raise ValueError("limit_price is required for limit orders")

        if limit_price <= 0:
            raise ValueError("limit_price must be greater than zero")

    if cash_balance is not None and cash_balance < 0:
        raise ValueError("cash_balance cannot be negative")

    if current_position_quantity is not None and current_position_quantity < 0:
        raise ValueError("current_position_quantity cannot be negative")

    if side == OrderSide.SELL and current_position_quantity is not None:
        if quantity > current_position_quantity:
            raise ValueError("sell quantity cannot exceed current position quantity")


def estimate_order_price(
    order_type: OrderType,
    estimated_price: float,
    limit_price: float | None = None,
) -> float:
    """Estimate order price for preview purposes."""
    if estimated_price <= 0:
        raise ValueError("estimated_price must be greater than zero")

    if order_type == OrderType.MARKET:
        return float(estimated_price)

    if limit_price is None:
        raise ValueError("limit_price is required for limit orders")

    if limit_price <= 0:
        raise ValueError("limit_price must be greater than zero")

    return float(limit_price)


def calculate_estimated_order_value(
    quantity: float,
    order_price: float,
) -> float:
    """Calculate gross order value."""
    if quantity <= 0:
        raise ValueError("quantity must be greater than zero")

    if order_price <= 0:
        raise ValueError("order_price must be greater than zero")

    return float(quantity * order_price)


def calculate_order_commission(
    order_value: float,
    commission_rate_pct: float = 0.0,
    minimum_commission: float = 0.0,
) -> float:
    """Calculate estimated commission."""
    if order_value < 0:
        raise ValueError("order_value cannot be negative")

    if commission_rate_pct < 0:
        raise ValueError("commission_rate_pct cannot be negative")

    if minimum_commission < 0:
        raise ValueError("minimum_commission cannot be negative")

    percentage_commission = order_value * (commission_rate_pct / 100)

    return float(max(percentage_commission, minimum_commission))


def calculate_cash_impact(
    side: OrderSide,
    order_value: float,
    commission: float = 0.0,
) -> float:
    """Calculate cash impact from simulated order."""
    if order_value < 0:
        raise ValueError("order_value cannot be negative")

    if commission < 0:
        raise ValueError("commission cannot be negative")

    if side == OrderSide.BUY:
        return float(-(order_value + commission))

    return float(order_value - commission)


def check_buying_power(
    side: OrderSide,
    cash_balance: float,
    order_value: float,
    commission: float = 0.0,
) -> bool:
    """Check whether cash balance can support a buy order."""
    if cash_balance < 0:
        raise ValueError("cash_balance cannot be negative")

    if order_value < 0:
        raise ValueError("order_value cannot be negative")

    if commission < 0:
        raise ValueError("commission cannot be negative")

    if side == OrderSide.SELL:
        return True

    return cash_balance >= order_value + commission


def build_order_ticket(
    account_id: str,
    ticker: str,
    side: OrderSide,
    quantity: float,
    order_type: OrderType,
    estimated_price: float,
    limit_price: float | None = None,
    cash_balance: float | None = None,
    current_position_quantity: float | None = None,
    commission_rate_pct: float = 0.0,
    minimum_commission: float = 0.0,
) -> dict[str, Any]:
    """Build a simulated order ticket with preview fields."""
    order_price = estimate_order_price(
        order_type=order_type,
        estimated_price=estimated_price,
        limit_price=limit_price,
    )

    order_value = calculate_estimated_order_value(
        quantity=quantity,
        order_price=order_price,
    )

    commission = calculate_order_commission(
        order_value=order_value,
        commission_rate_pct=commission_rate_pct,
        minimum_commission=minimum_commission,
    )

    validate_order_ticket_inputs(
        account_id=account_id,
        ticker=ticker,
        side=side,
        quantity=quantity,
        order_type=order_type,
        estimated_price=estimated_price,
        limit_price=limit_price,
        cash_balance=cash_balance,
        current_position_quantity=current_position_quantity,
        commission=commission,
    )

    if order_type == OrderType.MARKET:
        order = create_market_order(
            account_id=account_id,
            ticker=ticker,
            side=side,
            quantity=quantity,
        )
    else:
        order = create_limit_order(
            account_id=account_id,
            ticker=ticker,
            side=side,
            quantity=quantity,
            limit_price=float(limit_price),
        )

    cash_impact = calculate_cash_impact(
        side=side,
        order_value=order_value,
        commission=commission,
    )

    has_buying_power = True

    if cash_balance is not None:
        has_buying_power = check_buying_power(
            side=side,
            cash_balance=cash_balance,
            order_value=order_value,
            commission=commission,
        )

    estimated_cash_after_order = None
    if cash_balance is not None:
        estimated_cash_after_order = cash_balance + cash_impact

    ticket = {
        "order": order,
        "order_id": order.order_id,
        "account_id": account_id,
        "ticker": order.ticker,
        "side": side.value,
        "quantity": float(quantity),
        "order_type": order_type.value,
        "estimated_price": float(estimated_price),
        "limit_price": limit_price,
        "order_price": order_price,
        "estimated_order_value": order_value,
        "estimated_commission": commission,
        "estimated_cash_impact": cash_impact,
        "cash_balance": cash_balance,
        "estimated_cash_after_order": estimated_cash_after_order,
        "has_buying_power": has_buying_power,
        "current_position_quantity": current_position_quantity,
        "is_valid": has_buying_power,
        "rejection_reason": None if has_buying_power else "Insufficient buying power",
    }

    return ticket


def build_order_preview_table_row(order_ticket: dict[str, Any]) -> dict[str, Any]:
    """Convert an order ticket into a table-friendly preview row."""
    return {
        "order_id": order_ticket["order_id"],
        "ticker": order_ticket["ticker"],
        "side": order_ticket["side"],
        "order_type": order_ticket["order_type"],
        "quantity": order_ticket["quantity"],
        "order_price": order_ticket["order_price"],
        "estimated_order_value": order_ticket["estimated_order_value"],
        "estimated_commission": order_ticket["estimated_commission"],
        "estimated_cash_impact": order_ticket["estimated_cash_impact"],
        "cash_balance": order_ticket["cash_balance"],
        "estimated_cash_after_order": order_ticket["estimated_cash_after_order"],
        "has_buying_power": order_ticket["has_buying_power"],
        "is_valid": order_ticket["is_valid"],
        "rejection_reason": order_ticket["rejection_reason"],
    }


def serialize_order(order: PaperOrder) -> dict[str, Any]:
    """Serialize PaperOrder dataclass for display or export."""
    data = asdict(order)
    data["side"] = order.side.value
    data["order_type"] = order.order_type.value
    data["status"] = order.status.value
    return data
