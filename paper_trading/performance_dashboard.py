from __future__ import annotations

from typing import Any

import pandas as pd

from paper_trading.closed_trades_ledger import (
    build_closed_trades_dataframe,
    build_closed_trades_summary,
)
from paper_trading.equity_curve import build_equity_curve_summary
from paper_trading.models import ClosedPaperTrade, PaperPosition, PaperTradingAccount
from paper_trading.positions_ledger import build_open_positions_summary


def calculate_average_win(closed_trades: list[ClosedPaperTrade]) -> float:
    """Calculate average realized P/L for winning trades."""
    if not closed_trades:
        return 0.0

    closed_df = build_closed_trades_dataframe(closed_trades)
    winning_trades = closed_df[closed_df["realized_pnl"] > 0]

    if winning_trades.empty:
        return 0.0

    return float(winning_trades["realized_pnl"].mean())


def calculate_average_loss(closed_trades: list[ClosedPaperTrade]) -> float:
    """Calculate average realized P/L for losing trades."""
    if not closed_trades:
        return 0.0

    closed_df = build_closed_trades_dataframe(closed_trades)
    losing_trades = closed_df[closed_df["realized_pnl"] < 0]

    if losing_trades.empty:
        return 0.0

    return float(losing_trades["realized_pnl"].mean())


def calculate_gross_profit(closed_trades: list[ClosedPaperTrade]) -> float:
    """Calculate total realized profit from winning trades."""
    if not closed_trades:
        return 0.0

    closed_df = build_closed_trades_dataframe(closed_trades)
    winning_trades = closed_df[closed_df["realized_pnl"] > 0]

    if winning_trades.empty:
        return 0.0

    return float(winning_trades["realized_pnl"].sum())


def calculate_gross_loss(closed_trades: list[ClosedPaperTrade]) -> float:
    """Calculate absolute total realized loss from losing trades."""
    if not closed_trades:
        return 0.0

    closed_df = build_closed_trades_dataframe(closed_trades)
    losing_trades = closed_df[closed_df["realized_pnl"] < 0]

    if losing_trades.empty:
        return 0.0

    return float(abs(losing_trades["realized_pnl"].sum()))


def calculate_profit_factor(closed_trades: list[ClosedPaperTrade]) -> float:
    """Calculate profit factor as gross profit divided by gross loss."""
    gross_profit = calculate_gross_profit(closed_trades)
    gross_loss = calculate_gross_loss(closed_trades)

    if gross_loss == 0:
        if gross_profit > 0:
            return float("inf")
        return 0.0

    return float(gross_profit / gross_loss)


def calculate_expectancy(closed_trades: list[ClosedPaperTrade]) -> float:
    """Calculate average expected realized P/L per closed trade."""
    if not closed_trades:
        return 0.0

    closed_df = build_closed_trades_dataframe(closed_trades)

    return float(closed_df["realized_pnl"].mean())


def classify_performance_status(
    total_return_pct: float,
    max_drawdown_pct: float,
    profit_factor: float,
    win_rate_pct: float,
) -> str:
    """Classify paper trading performance status."""
    if total_return_pct > 0 and profit_factor >= 1.5 and win_rate_pct >= 50:
        return "Strong"

    if total_return_pct >= 0 and profit_factor >= 1.0:
        return "Stable"

    if max_drawdown_pct <= -10 or total_return_pct < 0:
        return "Needs Review"

    return "Developing"


def build_performance_dashboard_metrics(
    account: PaperTradingAccount,
    positions: list[PaperPosition],
    closed_trades: list[ClosedPaperTrade],
    equity_curve_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build dashboard-ready paper trading performance metrics."""
    open_summary = build_open_positions_summary(positions)
    closed_summary = build_closed_trades_summary(closed_trades)
    equity_summary = build_equity_curve_summary(equity_curve_records)

    latest_equity = (
        equity_summary["latest_equity"]
        if equity_summary["record_count"] > 0
        else account.cash_balance + open_summary["total_market_value"]
    )

    total_return_pct = (
        equity_summary["total_return_pct"]
        if equity_summary["record_count"] > 0
        else ((latest_equity - account.starting_cash) / account.starting_cash * 100)
    )

    max_drawdown_pct = (
        equity_summary["max_drawdown_pct"]
        if equity_summary["record_count"] > 0
        else 0.0
    )

    average_win = calculate_average_win(closed_trades)
    average_loss = calculate_average_loss(closed_trades)
    gross_profit = calculate_gross_profit(closed_trades)
    gross_loss = calculate_gross_loss(closed_trades)
    profit_factor = calculate_profit_factor(closed_trades)
    expectancy = calculate_expectancy(closed_trades)

    performance_status = classify_performance_status(
        total_return_pct=float(total_return_pct),
        max_drawdown_pct=float(max_drawdown_pct),
        profit_factor=float(profit_factor),
        win_rate_pct=float(closed_summary["win_rate_pct"]),
    )

    return {
        "account_id": account.account_id,
        "starting_cash": float(account.starting_cash),
        "cash_balance": float(account.cash_balance),
        "latest_equity": float(latest_equity),
        "total_return_pct": float(total_return_pct),
        "peak_equity": float(equity_summary["peak_equity"]),
        "max_drawdown_pct": float(max_drawdown_pct),
        "open_position_count": int(open_summary["position_count"]),
        "closed_trade_count": int(closed_summary["closed_trade_count"]),
        "win_count": int(closed_summary["win_count"]),
        "loss_count": int(closed_summary["loss_count"]),
        "breakeven_count": int(closed_summary["breakeven_count"]),
        "win_rate_pct": float(closed_summary["win_rate_pct"]),
        "total_realized_pnl": float(closed_summary["total_realized_pnl"]),
        "total_unrealized_pnl": float(open_summary["total_unrealized_pnl"]),
        "average_win": float(average_win),
        "average_loss": float(average_loss),
        "gross_profit": float(gross_profit),
        "gross_loss": float(gross_loss),
        "profit_factor": float(profit_factor),
        "expectancy": float(expectancy),
        "performance_status": performance_status,
    }


def build_performance_dashboard_dataframe(
    dashboard_metrics: dict[str, Any],
) -> pd.DataFrame:
    """Build table-ready dashboard metrics DataFrame."""
    return pd.DataFrame([dashboard_metrics])


def build_performance_scorecard(
    dashboard_metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build scorecard rows for dashboard rendering."""
    return [
        {
            "metric": "Latest Equity",
            "value": dashboard_metrics["latest_equity"],
            "format": "currency",
            "category": "Account",
        },
        {
            "metric": "Total Return %",
            "value": dashboard_metrics["total_return_pct"],
            "format": "percent",
            "category": "Account",
        },
        {
            "metric": "Max Drawdown %",
            "value": dashboard_metrics["max_drawdown_pct"],
            "format": "percent",
            "category": "Risk",
        },
        {
            "metric": "Win Rate %",
            "value": dashboard_metrics["win_rate_pct"],
            "format": "percent",
            "category": "Trades",
        },
        {
            "metric": "Profit Factor",
            "value": dashboard_metrics["profit_factor"],
            "format": "number",
            "category": "Trades",
        },
        {
            "metric": "Expectancy",
            "value": dashboard_metrics["expectancy"],
            "format": "currency",
            "category": "Trades",
        },
        {
            "metric": "Realized P/L",
            "value": dashboard_metrics["total_realized_pnl"],
            "format": "currency",
            "category": "P/L",
        },
        {
            "metric": "Unrealized P/L",
            "value": dashboard_metrics["total_unrealized_pnl"],
            "format": "currency",
            "category": "P/L",
        },
        {
            "metric": "Performance Status",
            "value": dashboard_metrics["performance_status"],
            "format": "text",
            "category": "Status",
        },
    ]


def build_performance_scorecard_dataframe(
    dashboard_metrics: dict[str, Any],
) -> pd.DataFrame:
    """Build table-ready performance scorecard DataFrame."""
    return pd.DataFrame(build_performance_scorecard(dashboard_metrics))
