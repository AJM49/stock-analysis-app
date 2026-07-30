from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from paper_trading.closed_trades_ledger import build_closed_trades_summary
from paper_trading.models import ClosedPaperTrade, PaperPosition, PaperTradingAccount
from paper_trading.positions_ledger import build_open_positions_summary


def calculate_total_account_equity(
    cash_balance: float,
    open_positions_market_value: float,
) -> float:
    """Calculate total paper account equity."""
    if cash_balance < 0:
        raise ValueError("cash_balance cannot be negative")

    if open_positions_market_value < 0:
        raise ValueError("open_positions_market_value cannot be negative")

    return float(cash_balance + open_positions_market_value)


def calculate_total_return_pct(
    current_equity: float,
    starting_cash: float,
) -> float:
    """Calculate total return percentage from starting cash."""
    if current_equity < 0:
        raise ValueError("current_equity cannot be negative")

    if starting_cash <= 0:
        raise ValueError("starting_cash must be greater than zero")

    return float((current_equity - starting_cash) / starting_cash * 100)


def calculate_drawdown_pct(
    current_equity: float,
    peak_equity: float,
) -> float:
    """Calculate drawdown percentage from peak equity."""
    if current_equity < 0:
        raise ValueError("current_equity cannot be negative")

    if peak_equity <= 0:
        raise ValueError("peak_equity must be greater than zero")

    return float((current_equity - peak_equity) / peak_equity * 100)


def build_equity_curve_record(
    account: PaperTradingAccount,
    positions: list[PaperPosition],
    closed_trades: list[ClosedPaperTrade],
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Build one equity curve record from current paper trading state."""
    if timestamp is None:
        timestamp = datetime.now(UTC)

    open_summary = build_open_positions_summary(positions)
    closed_summary = build_closed_trades_summary(closed_trades)

    cash_balance = float(account.cash_balance)
    open_market_value = float(open_summary["total_market_value"])
    total_equity = calculate_total_account_equity(
        cash_balance=cash_balance,
        open_positions_market_value=open_market_value,
    )

    total_return_pct = calculate_total_return_pct(
        current_equity=total_equity,
        starting_cash=float(account.starting_cash),
    )

    return {
        "timestamp": timestamp,
        "account_id": account.account_id,
        "starting_cash": float(account.starting_cash),
        "cash_balance": cash_balance,
        "open_positions_market_value": open_market_value,
        "total_equity": total_equity,
        "open_position_count": int(open_summary["position_count"]),
        "closed_trade_count": int(closed_summary["closed_trade_count"]),
        "total_unrealized_pnl": float(open_summary["total_unrealized_pnl"]),
        "total_unrealized_pnl_pct": float(open_summary["total_unrealized_pnl_pct"]),
        "total_realized_pnl": float(closed_summary["total_realized_pnl"]),
        "win_rate_pct": float(closed_summary["win_rate_pct"]),
        "total_return_pct": total_return_pct,
    }


def add_equity_curve_record(
    equity_curve_records: list[dict[str, Any]],
    record: dict[str, Any],
) -> list[dict[str, Any]]:
    """Add one equity curve record and keep records sorted by timestamp."""
    return sorted(
        [*equity_curve_records, record],
        key=lambda item: item["timestamp"],
    )


def build_equity_curve_dataframe(
    equity_curve_records: list[dict[str, Any]],
) -> pd.DataFrame:
    """Build table-ready equity curve DataFrame."""
    return pd.DataFrame(
        equity_curve_records,
        columns=[
            "timestamp",
            "account_id",
            "starting_cash",
            "cash_balance",
            "open_positions_market_value",
            "total_equity",
            "open_position_count",
            "closed_trade_count",
            "total_unrealized_pnl",
            "total_unrealized_pnl_pct",
            "total_realized_pnl",
            "win_rate_pct",
            "total_return_pct",
        ],
    )


def add_equity_curve_drawdown_columns(
    equity_curve_df: pd.DataFrame,
) -> pd.DataFrame:
    """Add running peak equity and drawdown columns."""
    if equity_curve_df.empty:
        return pd.DataFrame(
            columns=[
                *equity_curve_df.columns,
                "peak_equity",
                "drawdown_dollars",
                "drawdown_pct",
            ]
        )

    if "total_equity" not in equity_curve_df.columns:
        raise ValueError("equity_curve_df must include total_equity")

    result = equity_curve_df.copy()
    result["peak_equity"] = result["total_equity"].cummax()
    result["drawdown_dollars"] = result["total_equity"] - result["peak_equity"]
    result["drawdown_pct"] = (
        result["drawdown_dollars"] / result["peak_equity"] * 100
    )

    return result


def build_equity_curve_summary(
    equity_curve_records: list[dict[str, Any]],
) -> dict[str, float | int | None]:
    """Build summary metrics for the paper trading equity curve."""
    if not equity_curve_records:
        return {
            "record_count": 0,
            "starting_cash": 0.0,
            "latest_equity": 0.0,
            "peak_equity": 0.0,
            "lowest_equity": 0.0,
            "total_return_pct": 0.0,
            "max_drawdown_dollars": 0.0,
            "max_drawdown_pct": 0.0,
            "latest_cash_balance": 0.0,
            "latest_open_market_value": 0.0,
            "latest_realized_pnl": 0.0,
            "latest_unrealized_pnl": 0.0,
        }

    equity_df = build_equity_curve_dataframe(equity_curve_records)
    equity_df = add_equity_curve_drawdown_columns(equity_df)

    latest = equity_df.iloc[-1]

    return {
        "record_count": int(len(equity_df)),
        "starting_cash": float(latest["starting_cash"]),
        "latest_equity": float(latest["total_equity"]),
        "peak_equity": float(equity_df["peak_equity"].max()),
        "lowest_equity": float(equity_df["total_equity"].min()),
        "total_return_pct": float(latest["total_return_pct"]),
        "max_drawdown_dollars": float(equity_df["drawdown_dollars"].min()),
        "max_drawdown_pct": float(equity_df["drawdown_pct"].min()),
        "latest_cash_balance": float(latest["cash_balance"]),
        "latest_open_market_value": float(latest["open_positions_market_value"]),
        "latest_realized_pnl": float(latest["total_realized_pnl"]),
        "latest_unrealized_pnl": float(latest["total_unrealized_pnl"]),
    }


def build_equity_curve_chart_data(
    equity_curve_records: list[dict[str, Any]],
) -> pd.DataFrame:
    """Build chart-ready equity curve data."""
    equity_df = build_equity_curve_dataframe(equity_curve_records)

    if equity_df.empty:
        return pd.DataFrame(
            columns=[
                "timestamp",
                "total_equity",
                "cash_balance",
                "open_positions_market_value",
                "total_realized_pnl",
                "total_unrealized_pnl",
            ]
        )

    chart_columns = [
        "timestamp",
        "total_equity",
        "cash_balance",
        "open_positions_market_value",
        "total_realized_pnl",
        "total_unrealized_pnl",
    ]

    return equity_df[chart_columns].copy()
