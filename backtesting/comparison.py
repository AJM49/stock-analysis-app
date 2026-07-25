from __future__ import annotations

from typing import Any

import pandas as pd

from backtesting.engine import BacktestEngine
from strategies.base_strategy import BaseStrategy


def compare_strategies(
    price_data: pd.DataFrame,
    ticker: str,
    strategies: list[BaseStrategy],
    starting_cash: float = 10_000.0,
    trade_size_pct: float = 1.0,
) -> dict[str, Any]:
    """Run multiple strategies on the same price data."""
    if not strategies:
        raise ValueError("strategies cannot be empty")

    results = []

    for strategy in strategies:
        engine = BacktestEngine(
            strategy=strategy,
            ticker=ticker,
            starting_cash=starting_cash,
            trade_size_pct=trade_size_pct,
        )

        result = engine.run(price_data)

        results.append(
            {
                "strategy_name": result["strategy_name"],
                "starting_cash": result["starting_cash"],
                "ending_value": result["ending_value"],
                "total_return_pct": result["total_return_pct"],
                "max_drawdown_pct": result["max_drawdown_pct"],
                "number_of_trades": result["number_of_trades"],
                "completed_trades": result["completed_trades"],
                "win_rate_pct": result["win_rate_pct"],
                "exposure_pct": result["exposure_pct"],
                "annualized_return_pct": result["annualized_return_pct"],
                "annualized_volatility_pct": result["annualized_volatility_pct"],
                "sharpe_ratio": result["sharpe_ratio"],
                "sortino_ratio": result["sortino_ratio"],
                "risk_max_drawdown_pct": result["risk_max_drawdown_pct"],
                "drawdown_duration": result["drawdown_duration"],
                "value_at_risk_95_pct": result["value_at_risk_95_pct"],
                "conditional_value_at_risk_95_pct": result[
                    "conditional_value_at_risk_95_pct"
                ],
                "calmar_ratio": result["calmar_ratio"],
                "result": result,
            }
        )

    summary_df = pd.DataFrame(
        [
            {
                key: value
                for key, value in row.items()
                if key != "result"
            }
            for row in results
        ]
    )

    best_return_row = summary_df.sort_values(
        by="total_return_pct",
        ascending=False,
    ).iloc[0]

    lowest_drawdown_row = summary_df.sort_values(
        by="max_drawdown_pct",
        ascending=False,
    ).iloc[0]

    best_sharpe_row = summary_df.sort_values(
        by="sharpe_ratio",
        ascending=False,
    ).iloc[0]

    best_calmar_row = summary_df.sort_values(
        by="calmar_ratio",
        ascending=False,
    ).iloc[0]

    return {
        "ticker": ticker.upper(),
        "starting_cash": float(starting_cash),
        "summary": summary_df,
        "results": results,
        "best_return_strategy": best_return_row["strategy_name"],
        "lowest_drawdown_strategy": lowest_drawdown_row["strategy_name"],
        "best_sharpe_strategy": best_sharpe_row["strategy_name"],
        "best_calmar_strategy": best_calmar_row["strategy_name"],
    }
