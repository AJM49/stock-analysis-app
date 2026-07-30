from __future__ import annotations

from typing import Iterable

import pandas as pd

from paper_trading.execution_engine import (
    update_position_after_buy,
    update_position_after_sell,
)
from paper_trading.models import (
    ClosedPaperTrade,
    OrderSide,
    PaperPosition,
    PaperTrade,
)


def normalize_ticker(ticker: str) -> str:
    """Normalize ticker symbols for ledger lookups."""
    if not ticker or not ticker.strip():
        raise ValueError("ticker cannot be empty")

    return ticker.strip().upper()


def get_position_by_ticker(
    positions: Iterable[PaperPosition],
    ticker: str,
) -> PaperPosition | None:
    """Find an open position by ticker."""
    clean_ticker = normalize_ticker(ticker)

    for position in positions:
        if position.ticker == clean_ticker:
            return position

    return None


def upsert_position(
    positions: list[PaperPosition],
    updated_position: PaperPosition | None,
    ticker: str,
) -> list[PaperPosition]:
    """Insert, replace, or remove a position from the open positions ledger."""
    clean_ticker = normalize_ticker(ticker)

    remaining_positions = [
        position for position in positions if position.ticker != clean_ticker
    ]

    if updated_position is not None and updated_position.quantity > 0:
        remaining_positions.append(updated_position)

    return sorted(remaining_positions, key=lambda position: position.ticker)


def apply_trade_to_positions(
    positions: list[PaperPosition],
    trade: PaperTrade,
) -> tuple[list[PaperPosition], ClosedPaperTrade | None]:
    """Apply a filled paper trade to the open positions ledger."""
    current_position = get_position_by_ticker(
        positions=positions,
        ticker=trade.ticker,
    )

    closed_trade = None

    if trade.side == OrderSide.BUY:
        updated_position = update_position_after_buy(
            account_id=trade.account_id,
            ticker=trade.ticker,
            current_position=current_position,
            quantity=trade.quantity,
            fill_price=trade.fill_price,
        )
    else:
        if current_position is None:
            raise ValueError("cannot sell a position that does not exist")

        updated_position, closed_trade = update_position_after_sell(
            current_position=current_position,
            quantity=trade.quantity,
            fill_price=trade.fill_price,
        )

    updated_positions = upsert_position(
        positions=positions,
        updated_position=updated_position,
        ticker=trade.ticker,
    )

    return updated_positions, closed_trade


def build_open_positions_dataframe(
    positions: list[PaperPosition],
) -> pd.DataFrame:
    """Build table-ready open positions ledger."""
    rows = []

    for position in positions:
        rows.append(
            {
                "account_id": position.account_id,
                "ticker": position.ticker,
                "quantity": position.quantity,
                "average_cost": position.average_cost,
                "current_price": position.current_price,
                "cost_basis": position.cost_basis,
                "market_value": position.market_value,
                "unrealized_pnl": position.unrealized_pnl,
                "unrealized_pnl_pct": position.unrealized_pnl_pct,
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "account_id",
            "ticker",
            "quantity",
            "average_cost",
            "current_price",
            "cost_basis",
            "market_value",
            "unrealized_pnl",
            "unrealized_pnl_pct",
        ],
    )


def build_open_positions_summary(
    positions: list[PaperPosition],
) -> dict[str, float | int]:
    """Build summary metrics for open positions ledger."""
    if not positions:
        return {
            "position_count": 0,
            "total_cost_basis": 0.0,
            "total_market_value": 0.0,
            "total_unrealized_pnl": 0.0,
            "total_unrealized_pnl_pct": 0.0,
            "largest_position_value": 0.0,
        }

    positions_df = build_open_positions_dataframe(positions)

    total_cost_basis = float(positions_df["cost_basis"].sum())
    total_market_value = float(positions_df["market_value"].sum())
    total_unrealized_pnl = float(positions_df["unrealized_pnl"].sum())

    if total_cost_basis == 0:
        total_unrealized_pnl_pct = 0.0
    else:
        total_unrealized_pnl_pct = total_unrealized_pnl / total_cost_basis * 100

    return {
        "position_count": len(positions),
        "total_cost_basis": total_cost_basis,
        "total_market_value": total_market_value,
        "total_unrealized_pnl": total_unrealized_pnl,
        "total_unrealized_pnl_pct": float(total_unrealized_pnl_pct),
        "largest_position_value": float(positions_df["market_value"].max()),
    }


def update_position_prices(
    positions: list[PaperPosition],
    price_lookup: dict[str, float],
) -> list[PaperPosition]:
    """Update current prices for open positions."""
    updated_positions = []

    for position in positions:
        price = price_lookup.get(position.ticker)

        if price is None:
            updated_positions.append(position)
            continue

        if price <= 0:
            raise ValueError("price_lookup values must be greater than zero")

        updated_positions.append(
            PaperPosition(
                account_id=position.account_id,
                ticker=position.ticker,
                quantity=position.quantity,
                average_cost=position.average_cost,
                current_price=float(price),
            )
        )

    return sorted(updated_positions, key=lambda position: position.ticker)
