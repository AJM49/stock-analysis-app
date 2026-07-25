from __future__ import annotations

import numpy as np
import pandas as pd

from portfolio_optimization.portfolio_math import build_portfolio_statistics


def validate_asset_list(assets: list[str]) -> None:
    """Validate list of portfolio assets."""
    if not assets:
        raise ValueError("assets cannot be empty")

    if len(assets) < 2:
        raise ValueError("assets must contain at least two tickers")

    cleaned_assets = [asset.strip().upper() for asset in assets]

    if any(not asset for asset in cleaned_assets):
        raise ValueError("assets cannot contain blank tickers")

    if len(set(cleaned_assets)) != len(cleaned_assets):
        raise ValueError("assets cannot contain duplicate tickers")


def build_equal_weight_allocations(assets: list[str]) -> pd.DataFrame:
    """Build equal-weight allocations for a list of assets."""
    validate_asset_list(assets)

    cleaned_assets = [asset.strip().upper() for asset in assets]
    weight = 1.0 / len(cleaned_assets)

    allocations = pd.DataFrame(
        {
            "ticker": cleaned_assets,
            "weight": [weight] * len(cleaned_assets),
            "weight_pct": [weight * 100] * len(cleaned_assets),
        }
    )

    return allocations


def calculate_equal_weight_vector(asset_count: int) -> np.ndarray:
    """Create equal-weight vector for a portfolio."""
    if asset_count < 2:
        raise ValueError("asset_count must be at least 2")

    return np.array([1.0 / asset_count] * asset_count)


def run_equal_weight_optimizer(
    price_data: pd.DataFrame,
    risk_free_rate: float = 0.0,
) -> dict[str, object]:
    """Run equal-weight portfolio optimizer from multi-asset price data."""
    assets = list(price_data.columns)
    validate_asset_list(assets)

    weights = calculate_equal_weight_vector(len(assets))
    allocations = build_equal_weight_allocations(assets)

    statistics = build_portfolio_statistics(
        price_data=price_data,
        weights=weights,
        risk_free_rate=risk_free_rate,
    )

    return {
        "optimizer_name": "Equal Weight",
        "assets": [asset.strip().upper() for asset in assets],
        "weights": weights,
        "allocations": allocations,
        "portfolio_return": statistics["portfolio_return"],
        "portfolio_volatility": statistics["portfolio_volatility"],
        "sharpe_ratio": statistics["sharpe_ratio"],
        "asset_returns": statistics["asset_returns"],
        "mean_returns": statistics["mean_returns"],
        "covariance_matrix": statistics["covariance_matrix"],
    }
