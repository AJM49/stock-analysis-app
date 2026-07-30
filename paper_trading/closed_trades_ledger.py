from __future__ import annotations

from typing import Iterable

import pandas as pd

from paper_trading.models import ClosedPaperTrade


def normalize_ticker(ticker: str) -> str:
    """Normalize ticker symbols for closed trade lookup."""
    if not ticker or not ticker.strip():
        raise ValueError("ticker cannot be empty")

    return ticker.strip().upper()


def classify_closed_trade_result(closed_trade: ClosedPaperTrade) -> str:
    """Classify a closed trade as Win, Loss, or Breakeven."""
    if closed_trade.realized_pnl > 0:
        return "Win"

    if closed_trade.realized_pnl < 0:
        return "Loss"

    return "Breakeven"


def add_closed_trade(
    closed_trades: list[ClosedPaperTrade],
    closed_trade: ClosedPaperTrade,
) -> list[ClosedPaperTrade]:
    """Add a closed trade to the closed trades ledger."""
    return sorted(
        [*closed_trades, closed_trade],
        key=lambda trade: (trade.closed_at, trade.ticker),
    )


def get_closed_trades_by_ticker(
    closed_trades: Iterable[ClosedPaperTrade],
    ticker: str,
) -> list[ClosedPaperTrade]:
    """Get all closed trades for a ticker."""
    clean_ticker = normalize_ticker(ticker)

    return [
        trade
        for trade in closed_trades
        if trade.ticker == clean_ticker
    ]


def calculate_closed_trade_entry_value(closed_trade: ClosedPaperTrade) -> float:
    """Calculate original entry value for a closed trade."""
    return float(closed_trade.quantity * closed_trade.entry_price)


def calculate_closed_trade_exit_value(closed_trade: ClosedPaperTrade) -> float:
    """Calculate exit value before commission for a closed trade."""
    return float(closed_trade.quantity * closed_trade.exit_price)


def build_closed_trades_dataframe(
    closed_trades: list[ClosedPaperTrade],
) -> pd.DataFrame:
    """Build table-ready closed trades ledger."""
    rows = []

    for trade in closed_trades:
        rows.append(
            {
                "account_id": trade.account_id,
                "ticker": trade.ticker,
                "quantity": trade.quantity,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "entry_value": calculate_closed_trade_entry_value(trade),
                "exit_value": calculate_closed_trade_exit_value(trade),
                "commission": trade.commission,
                "realized_pnl": trade.realized_pnl,
                "realized_pnl_pct": trade.realized_pnl_pct,
                "result": classify_closed_trade_result(trade),
                "closed_at": trade.closed_at,
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "account_id",
            "ticker",
            "quantity",
            "entry_price",
            "exit_price",
            "entry_value",
            "exit_value",
            "commission",
            "realized_pnl",
            "realized_pnl_pct",
            "result",
            "closed_at",
        ],
    )


def build_closed_trades_summary(
    closed_trades: list[ClosedPaperTrade],
) -> dict[str, float | int | str | None]:
    """Build performance summary for closed trades ledger."""
    if not closed_trades:
        return {
            "closed_trade_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "breakeven_count": 0,
            "win_rate_pct": 0.0,
            "total_realized_pnl": 0.0,
            "average_realized_pnl": 0.0,
            "average_realized_pnl_pct": 0.0,
            "best_trade_ticker": None,
            "best_trade_realized_pnl": 0.0,
            "worst_trade_ticker": None,
            "worst_trade_realized_pnl": 0.0,
        }

    closed_df = build_closed_trades_dataframe(closed_trades)

    win_count = int((closed_df["result"] == "Win").sum())
    loss_count = int((closed_df["result"] == "Loss").sum())
    breakeven_count = int((closed_df["result"] == "Breakeven").sum())
    closed_trade_count = len(closed_df)

    win_rate_pct = win_count / closed_trade_count * 100

    best_trade = closed_df.sort_values(
        by="realized_pnl",
        ascending=False,
    ).iloc[0]

    worst_trade = closed_df.sort_values(
        by="realized_pnl",
        ascending=True,
    ).iloc[0]

    return {
        "closed_trade_count": closed_trade_count,
        "win_count": win_count,
        "loss_count": loss_count,
        "breakeven_count": breakeven_count,
        "win_rate_pct": float(win_rate_pct),
        "total_realized_pnl": float(closed_df["realized_pnl"].sum()),
        "average_realized_pnl": float(closed_df["realized_pnl"].mean()),
        "average_realized_pnl_pct": float(closed_df["realized_pnl_pct"].mean()),
        "best_trade_ticker": str(best_trade["ticker"]),
        "best_trade_realized_pnl": float(best_trade["realized_pnl"]),
        "worst_trade_ticker": str(worst_trade["ticker"]),
        "worst_trade_realized_pnl": float(worst_trade["realized_pnl"]),
    }


def calculate_realized_pnl_by_ticker(
    closed_trades: list[ClosedPaperTrade],
) -> pd.DataFrame:
    """Aggregate realized P/L by ticker."""
    if not closed_trades:
        return pd.DataFrame(
            columns=[
                "ticker",
                "closed_trade_count",
                "total_realized_pnl",
                "average_realized_pnl",
                "average_realized_pnl_pct",
                "win_count",
                "loss_count",
                "win_rate_pct",
            ]
        )

    closed_df = build_closed_trades_dataframe(closed_trades)

    grouped = (
        closed_df.groupby("ticker")
        .agg(
            closed_trade_count=("ticker", "count"),
            total_realized_pnl=("realized_pnl", "sum"),
            average_realized_pnl=("realized_pnl", "mean"),
            average_realized_pnl_pct=("realized_pnl_pct", "mean"),
            win_count=("result", lambda values: int((values == "Win").sum())),
            loss_count=("result", lambda values: int((values == "Loss").sum())),
        )
        .reset_index()
    )

    grouped["win_rate_pct"] = (
        grouped["win_count"] / grouped["closed_trade_count"] * 100
    )

    return grouped.sort_values(
        by="total_realized_pnl",
        ascending=False,
    ).reset_index(drop=True)
