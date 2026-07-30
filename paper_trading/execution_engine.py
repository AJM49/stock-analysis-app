from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from paper_trading.models import (
    ClosedPaperTrade,
    OrderSide,
    OrderStatus,
    OrderType,
    PaperOrder,
    PaperPosition,
    PaperTrade,
    PaperTradingAccount,
)


def validate_order_for_execution(
    order: PaperOrder,
    market_price: float,
    account: PaperTradingAccount,
    current_position: PaperPosition | None = None,
    commission: float = 0.0,
) -> None:
    """Validate whether a paper order can be executed."""
    if market_price <= 0:
        raise ValueError("market_price must be greater than zero")

    if commission < 0:
        raise ValueError("commission cannot be negative")

    if order.status != OrderStatus.PENDING:
        raise ValueError("only pending orders can be executed")

    if order.account_id != account.account_id:
        raise ValueError("order account_id must match account account_id")

    if order.side == OrderSide.BUY:
        estimated_cost = order.quantity * market_price + commission

        if estimated_cost > account.cash_balance:
            raise ValueError("insufficient cash to execute buy order")

    if order.side == OrderSide.SELL:
        if current_position is None:
            raise ValueError("current_position is required for sell orders")

        if current_position.ticker != order.ticker:
            raise ValueError("current_position ticker must match order ticker")

        if order.quantity > current_position.quantity:
            raise ValueError("sell quantity cannot exceed current position quantity")


def should_fill_order(order: PaperOrder, market_price: float) -> bool:
    """Determine whether an order should fill at the current market price."""
    if market_price <= 0:
        raise ValueError("market_price must be greater than zero")

    if order.order_type == OrderType.MARKET:
        return True

    if order.limit_price is None:
        raise ValueError("limit_price is required for limit orders")

    if order.side == OrderSide.BUY:
        return market_price <= order.limit_price

    return market_price >= order.limit_price


def build_filled_trade(
    order: PaperOrder,
    fill_price: float,
    commission: float = 0.0,
) -> PaperTrade:
    """Create a filled paper trade from an order."""
    if fill_price <= 0:
        raise ValueError("fill_price must be greater than zero")

    if commission < 0:
        raise ValueError("commission cannot be negative")

    return PaperTrade(
        trade_id=str(uuid4()),
        order_id=order.order_id,
        account_id=order.account_id,
        ticker=order.ticker,
        side=order.side,
        quantity=order.quantity,
        fill_price=fill_price,
        commission=commission,
        filled_at=datetime.now(UTC),
    )


def mark_order_filled(order: PaperOrder) -> PaperOrder:
    """Return a copy of the order marked as filled."""
    return replace(order, status=OrderStatus.FILLED)


def mark_order_rejected(order: PaperOrder) -> PaperOrder:
    """Return a copy of the order marked as rejected."""
    return replace(order, status=OrderStatus.REJECTED)


def update_account_after_trade(
    account: PaperTradingAccount,
    trade: PaperTrade,
) -> PaperTradingAccount:
    """Update paper account cash after a filled trade."""
    new_cash_balance = account.cash_balance + trade.net_cash_impact

    if new_cash_balance < 0:
        raise ValueError("trade would create negative cash balance")

    return replace(account, cash_balance=float(new_cash_balance))


def update_position_after_buy(
    account_id: str,
    ticker: str,
    current_position: PaperPosition | None,
    quantity: float,
    fill_price: float,
) -> PaperPosition:
    """Update or create position after a buy trade."""
    if quantity <= 0:
        raise ValueError("quantity must be greater than zero")

    if fill_price <= 0:
        raise ValueError("fill_price must be greater than zero")

    clean_ticker = ticker.strip().upper()

    if current_position is None:
        return PaperPosition(
            account_id=account_id,
            ticker=clean_ticker,
            quantity=quantity,
            average_cost=fill_price,
            current_price=fill_price,
        )

    if current_position.ticker != clean_ticker:
        raise ValueError("current_position ticker must match buy ticker")

    old_cost_basis = current_position.quantity * current_position.average_cost
    new_trade_value = quantity * fill_price
    new_quantity = current_position.quantity + quantity
    new_average_cost = (old_cost_basis + new_trade_value) / new_quantity

    return PaperPosition(
        account_id=account_id,
        ticker=clean_ticker,
        quantity=float(new_quantity),
        average_cost=float(new_average_cost),
        current_price=fill_price,
    )


def update_position_after_sell(
    current_position: PaperPosition,
    quantity: float,
    fill_price: float,
) -> tuple[PaperPosition | None, ClosedPaperTrade]:
    """Update position and create closed trade record after a sell trade."""
    if quantity <= 0:
        raise ValueError("quantity must be greater than zero")

    if fill_price <= 0:
        raise ValueError("fill_price must be greater than zero")

    if quantity > current_position.quantity:
        raise ValueError("sell quantity cannot exceed current position quantity")

    closed_trade = ClosedPaperTrade(
        account_id=current_position.account_id,
        ticker=current_position.ticker,
        quantity=quantity,
        entry_price=current_position.average_cost,
        exit_price=fill_price,
        commission=0.0,
        closed_at=datetime.now(UTC),
    )

    remaining_quantity = current_position.quantity - quantity

    if remaining_quantity == 0:
        return None, closed_trade

    updated_position = PaperPosition(
        account_id=current_position.account_id,
        ticker=current_position.ticker,
        quantity=float(remaining_quantity),
        average_cost=current_position.average_cost,
        current_price=fill_price,
    )

    return updated_position, closed_trade


def execute_paper_order(
    order: PaperOrder,
    account: PaperTradingAccount,
    market_price: float,
    current_position: PaperPosition | None = None,
    commission: float = 0.0,
) -> dict[str, Any]:
    """Execute a paper order and return updated state."""
    if not should_fill_order(order=order, market_price=market_price):
        return {
            "filled": False,
            "order": order,
            "updated_order": order,
            "trade": None,
            "updated_account": account,
            "updated_position": current_position,
            "closed_trade": None,
            "execution_status": "Not Filled",
            "execution_reason": "Limit price condition was not met.",
        }

    try:
        validate_order_for_execution(
            order=order,
            market_price=market_price,
            account=account,
            current_position=current_position,
            commission=commission,
        )
    except ValueError as error:
        rejected_order = mark_order_rejected(order)

        return {
            "filled": False,
            "order": order,
            "updated_order": rejected_order,
            "trade": None,
            "updated_account": account,
            "updated_position": current_position,
            "closed_trade": None,
            "execution_status": "Rejected",
            "execution_reason": str(error),
        }

    trade = build_filled_trade(
        order=order,
        fill_price=market_price,
        commission=commission,
    )

    updated_account = update_account_after_trade(
        account=account,
        trade=trade,
    )

    closed_trade = None

    if order.side == OrderSide.BUY:
        updated_position = update_position_after_buy(
            account_id=account.account_id,
            ticker=order.ticker,
            current_position=current_position,
            quantity=order.quantity,
            fill_price=market_price,
        )
    else:
        if current_position is None:
            raise ValueError("current_position is required for sell orders")

        updated_position, closed_trade = update_position_after_sell(
            current_position=current_position,
            quantity=order.quantity,
            fill_price=market_price,
        )

    updated_order = mark_order_filled(order)

    return {
        "filled": True,
        "order": order,
        "updated_order": updated_order,
        "trade": trade,
        "updated_account": updated_account,
        "updated_position": updated_position,
        "closed_trade": closed_trade,
        "execution_status": "Filled",
        "execution_reason": "Order filled successfully.",
    }


def build_execution_summary(execution_result: dict[str, Any]) -> dict[str, Any]:
    """Build table-friendly execution summary."""
    trade = execution_result["trade"]
    updated_account = execution_result["updated_account"]
    updated_position = execution_result["updated_position"]
    closed_trade = execution_result["closed_trade"]

    return {
        "filled": execution_result["filled"],
        "execution_status": execution_result["execution_status"],
        "execution_reason": execution_result["execution_reason"],
        "trade_id": trade.trade_id if trade else None,
        "ticker": trade.ticker if trade else None,
        "side": trade.side.value if trade else None,
        "quantity": trade.quantity if trade else None,
        "fill_price": trade.fill_price if trade else None,
        "gross_value": trade.gross_value if trade else None,
        "commission": trade.commission if trade else None,
        "net_cash_impact": trade.net_cash_impact if trade else None,
        "cash_balance_after_trade": updated_account.cash_balance,
        "position_quantity_after_trade": (
            updated_position.quantity if updated_position else 0.0
        ),
        "position_average_cost_after_trade": (
            updated_position.average_cost if updated_position else None
        ),
        "closed_trade_realized_pnl": (
            closed_trade.realized_pnl if closed_trade else None
        ),
        "closed_trade_realized_pnl_pct": (
            closed_trade.realized_pnl_pct if closed_trade else None
        ),
    }
