from __future__ import annotations

import numpy as np
import pandas as pd

from portfolio_optimization.portfolio_math import (
    build_portfolio_statistics,
    calculate_portfolio_return,
    calculate_portfolio_sharpe_ratio,
    calculate_portfolio_volatility,
)


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


def generate_random_weight_matrix(
    asset_count: int,
    simulation_count: int = 5000,
    random_seed: int = 42,
) -> np.ndarray:
    """Generate random long-only portfolio weights."""
    if asset_count < 2:
        raise ValueError("asset_count must be at least 2")

    if simulation_count < 1:
        raise ValueError("simulation_count must be at least 1")

    rng = np.random.default_rng(random_seed)
    raw_weights = rng.random((simulation_count, asset_count))

    return raw_weights / raw_weights.sum(axis=1, keepdims=True)


def run_minimum_volatility_optimizer(
    price_data: pd.DataFrame,
    simulation_count: int = 5000,
    risk_free_rate: float = 0.0,
    random_seed: int = 42,
) -> dict[str, object]:
    """Run minimum volatility optimizer using random portfolio search."""
    assets = list(price_data.columns)
    validate_asset_list(assets)

    equal_weights = calculate_equal_weight_vector(len(assets))

    base_statistics = build_portfolio_statistics(
        price_data=price_data,
        weights=equal_weights,
        risk_free_rate=risk_free_rate,
    )

    mean_returns = base_statistics["mean_returns"]
    covariance_matrix = base_statistics["covariance_matrix"]

    candidate_weights = generate_random_weight_matrix(
        asset_count=len(assets),
        simulation_count=simulation_count,
        random_seed=random_seed,
    )

    best_weights = None
    best_return = 0.0
    best_volatility = float("inf")
    best_sharpe_ratio = 0.0

    for weights in candidate_weights:
        portfolio_return = calculate_portfolio_return(weights, mean_returns)
        portfolio_volatility = calculate_portfolio_volatility(
            weights,
            covariance_matrix,
        )
        sharpe_ratio = calculate_portfolio_sharpe_ratio(
            portfolio_return=portfolio_return,
            portfolio_volatility=portfolio_volatility,
            risk_free_rate=risk_free_rate,
        )

        if portfolio_volatility < best_volatility:
            best_weights = weights
            best_return = portfolio_return
            best_volatility = portfolio_volatility
            best_sharpe_ratio = sharpe_ratio

    if best_weights is None:
        raise ValueError("minimum volatility optimization failed")

    cleaned_assets = [asset.strip().upper() for asset in assets]

    allocations = pd.DataFrame(
        {
            "ticker": cleaned_assets,
            "weight": best_weights,
            "weight_pct": best_weights * 100,
        }
    ).sort_values(
        by="weight",
        ascending=False,
    ).reset_index(drop=True)

    return {
        "optimizer_name": "Minimum Volatility",
        "assets": cleaned_assets,
        "weights": best_weights,
        "allocations": allocations,
        "portfolio_return": best_return,
        "portfolio_volatility": best_volatility,
        "sharpe_ratio": best_sharpe_ratio,
        "asset_returns": base_statistics["asset_returns"],
        "mean_returns": mean_returns,
        "covariance_matrix": covariance_matrix,
        "simulation_count": simulation_count,
    }
