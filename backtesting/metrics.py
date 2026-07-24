from __future__ import annotations

import pandas as pd


def calculate_total_return(starting_value: float, ending_value: float) -> float:
    """Calculate total return as a percentage."""
    if starting_value == 0:
        return 0.0

    return ((ending_value - starting_value) / starting_value) * 100


def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """Calculate maximum drawdown as a percentage."""
    if equity_curve.empty:
        return 0.0

    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max

    return float(drawdown.min() * 100)


def calculate_win_rate(trades_df: pd.DataFrame) -> float:
    """Calculate basic win rate from completed trades."""
    if trades_df.empty or "pnl" not in trades_df.columns:
        return 0.0

    completed_trades = trades_df[trades_df["pnl"].notna()]

    if completed_trades.empty:
        return 0.0

    wins = completed_trades[completed_trades["pnl"] > 0]

    return (len(wins) / len(completed_trades)) * 100
