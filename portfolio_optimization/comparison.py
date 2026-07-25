from __future__ import annotations

from typing import Any

import pandas as pd

from portfolio_optimization.optimizers import (
    run_equal_weight_optimizer,
    run_maximum_sharpe_optimizer,
    run_minimum_volatility_optimizer,
)


def build_optimizer_summary_row(result: dict[str, Any]) -> dict[str, Any]:
    """Build one summary row from an optimizer result."""
    return {
        "optimizer_name": result["optimizer_name"],
        "portfolio_return": result["portfolio_return"],
        "portfolio_return_pct": result["portfolio_return"] * 100,
        "portfolio_volatility": result["portfolio_volatility"],
        "portfolio_volatility_pct": result["portfolio_volatility"] * 100,
        "sharpe_ratio": result["sharpe_ratio"],
        "asset_count": len(result["assets"]),
        "allocations": result["allocations"],
        "result": result,
    }


def compare_portfolio_optimizers(
    price_data: pd.DataFrame,
    simulation_count: int = 5000,
    risk_free_rate: float = 0.0,
    random_seed: int = 42,
) -> dict[str, Any]:
    """Run portfolio optimizers and compare results."""
    if price_data.empty:
        raise ValueError("price_data cannot be empty")

    optimizer_results = [
        run_equal_weight_optimizer(
            price_data=price_data,
            risk_free_rate=risk_free_rate,
        ),
        run_minimum_volatility_optimizer(
            price_data=price_data,
            simulation_count=simulation_count,
            risk_free_rate=risk_free_rate,
            random_seed=random_seed,
        ),
        run_maximum_sharpe_optimizer(
            price_data=price_data,
            simulation_count=simulation_count,
            risk_free_rate=risk_free_rate,
            random_seed=random_seed,
        ),
    ]

    summary_rows = [
        build_optimizer_summary_row(result)
        for result in optimizer_results
    ]

    summary_df = pd.DataFrame(summary_rows)

    best_return_row = summary_df.sort_values(
        by="portfolio_return",
        ascending=False,
    ).iloc[0]

    lowest_volatility_row = summary_df.sort_values(
        by="portfolio_volatility",
        ascending=True,
    ).iloc[0]

    best_sharpe_row = summary_df.sort_values(
        by="sharpe_ratio",
        ascending=False,
    ).iloc[0]

    return {
        "summary": summary_df,
        "results": optimizer_results,
        "best_return_optimizer": best_return_row["optimizer_name"],
        "lowest_volatility_optimizer": lowest_volatility_row["optimizer_name"],
        "best_sharpe_optimizer": best_sharpe_row["optimizer_name"],
        "simulation_count": simulation_count,
        "risk_free_rate": risk_free_rate,
        "asset_count": price_data.shape[1],
    }


def build_allocation_comparison_table(
    comparison: dict[str, Any],
) -> pd.DataFrame:
    """Build side-by-side allocation table from optimizer comparison."""
    allocation_frames = []

    for result in comparison["results"]:
        allocation_df = result["allocations"][["ticker", "weight_pct"]].copy()
        allocation_df = allocation_df.rename(
            columns={
                "weight_pct": result["optimizer_name"],
            }
        )
        allocation_frames.append(allocation_df)

    merged = allocation_frames[0]

    for frame in allocation_frames[1:]:
        merged = merged.merge(frame, on="ticker", how="outer")

    return merged.fillna(0.0).sort_values(by="ticker").reset_index(drop=True)
