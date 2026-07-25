from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def validate_price_frame(price_data: pd.DataFrame) -> None:
    """Validate multi-asset price data."""
    if price_data.empty:
        raise ValueError("price_data cannot be empty")

    if price_data.shape[1] < 2:
        raise ValueError("price_data must contain at least two assets")

    if price_data.isna().all().any():
        raise ValueError("price_data contains an asset with all missing values")


def calculate_asset_returns(price_data: pd.DataFrame) -> pd.DataFrame:
    """Calculate daily percentage returns for each asset."""
    validate_price_frame(price_data)

    clean_prices = price_data.sort_index().ffill().dropna(how="all")
    returns = clean_prices.pct_change().dropna(how="all")

    return returns.fillna(0.0)


def calculate_mean_returns(
    asset_returns: pd.DataFrame,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> pd.Series:
    """Calculate annualized mean returns for each asset."""
    if asset_returns.empty:
        raise ValueError("asset_returns cannot be empty")

    return asset_returns.mean() * periods_per_year


def calculate_covariance_matrix(
    asset_returns: pd.DataFrame,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> pd.DataFrame:
    """Calculate annualized covariance matrix."""
    if asset_returns.empty:
        raise ValueError("asset_returns cannot be empty")

    return asset_returns.cov() * periods_per_year


def validate_weights(weights: np.ndarray, asset_count: int) -> None:
    """Validate portfolio weights."""
    if len(weights) != asset_count:
        raise ValueError("weights length must match asset count")

    if np.any(weights < 0):
        raise ValueError("weights cannot contain negative values")

    if not np.isclose(weights.sum(), 1.0):
        raise ValueError("weights must sum to 1.0")


def calculate_portfolio_return(
    weights: np.ndarray,
    mean_returns: pd.Series,
) -> float:
    """Calculate expected annualized portfolio return."""
    validate_weights(weights, len(mean_returns))

    return float(np.dot(weights, mean_returns))


def calculate_portfolio_volatility(
    weights: np.ndarray,
    covariance_matrix: pd.DataFrame,
) -> float:
    """Calculate expected annualized portfolio volatility."""
    validate_weights(weights, covariance_matrix.shape[0])

    variance = float(weights.T @ covariance_matrix.values @ weights)

    return float(np.sqrt(max(variance, 0.0)))


def calculate_portfolio_sharpe_ratio(
    portfolio_return: float,
    portfolio_volatility: float,
    risk_free_rate: float = 0.0,
) -> float:
    """Calculate Sharpe-style ratio for a portfolio."""
    if portfolio_volatility == 0:
        return 0.0

    return float((portfolio_return - risk_free_rate) / portfolio_volatility)


def build_portfolio_statistics(
    price_data: pd.DataFrame,
    weights: np.ndarray,
    risk_free_rate: float = 0.0,
) -> dict[str, object]:
    """Build reusable portfolio statistics from price data and weights."""
    validate_price_frame(price_data)

    asset_returns = calculate_asset_returns(price_data)
    mean_returns = calculate_mean_returns(asset_returns)
    covariance_matrix = calculate_covariance_matrix(asset_returns)

    portfolio_return = calculate_portfolio_return(weights, mean_returns)
    portfolio_volatility = calculate_portfolio_volatility(weights, covariance_matrix)
    sharpe_ratio = calculate_portfolio_sharpe_ratio(
        portfolio_return=portfolio_return,
        portfolio_volatility=portfolio_volatility,
        risk_free_rate=risk_free_rate,
    )

    return {
        "asset_returns": asset_returns,
        "mean_returns": mean_returns,
        "covariance_matrix": covariance_matrix,
        "portfolio_return": portfolio_return,
        "portfolio_volatility": portfolio_volatility,
        "sharpe_ratio": sharpe_ratio,
    }
