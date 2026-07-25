from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from portfolio_optimization.portfolio_math import (
    build_portfolio_statistics,
    calculate_asset_returns,
    calculate_covariance_matrix,
    calculate_mean_returns,
    calculate_portfolio_return,
    calculate_portfolio_sharpe_ratio,
    calculate_portfolio_volatility,
    validate_price_frame,
    validate_weights,
)


def build_sample_price_data() -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=6, freq="D")

    return pd.DataFrame(
        {
            "AAPL": [100, 101, 102, 103, 104, 105],
            "MSFT": [200, 202, 201, 203, 204, 206],
            "NVDA": [300, 303, 306, 309, 312, 315],
        },
        index=dates,
    )


def test_validate_price_frame_rejects_empty_data() -> None:
    with pytest.raises(ValueError, match="price_data cannot be empty"):
        validate_price_frame(pd.DataFrame())


def test_validate_price_frame_rejects_single_asset() -> None:
    price_data = pd.DataFrame({"AAPL": [100, 101, 102]})

    with pytest.raises(ValueError, match="at least two assets"):
        validate_price_frame(price_data)


def test_calculate_asset_returns() -> None:
    price_data = build_sample_price_data()
    returns = calculate_asset_returns(price_data)

    assert not returns.empty
    assert list(returns.columns) == ["AAPL", "MSFT", "NVDA"]
    assert len(returns) == len(price_data) - 1


def test_calculate_mean_returns() -> None:
    price_data = build_sample_price_data()
    returns = calculate_asset_returns(price_data)
    mean_returns = calculate_mean_returns(returns)

    assert isinstance(mean_returns, pd.Series)
    assert set(mean_returns.index) == {"AAPL", "MSFT", "NVDA"}


def test_calculate_covariance_matrix() -> None:
    price_data = build_sample_price_data()
    returns = calculate_asset_returns(price_data)
    covariance = calculate_covariance_matrix(returns)

    assert isinstance(covariance, pd.DataFrame)
    assert covariance.shape == (3, 3)


def test_validate_weights_rejects_bad_length() -> None:
    with pytest.raises(ValueError, match="weights length"):
        validate_weights(np.array([0.5, 0.5]), asset_count=3)


def test_validate_weights_rejects_negative_weights() -> None:
    with pytest.raises(ValueError, match="negative"):
        validate_weights(np.array([0.7, -0.2, 0.5]), asset_count=3)


def test_validate_weights_rejects_weights_that_do_not_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sum to 1.0"):
        validate_weights(np.array([0.4, 0.4, 0.4]), asset_count=3)


def test_calculate_portfolio_return() -> None:
    mean_returns = pd.Series(
        {
            "AAPL": 0.10,
            "MSFT": 0.20,
            "NVDA": 0.30,
        }
    )
    weights = np.array([0.25, 0.25, 0.50])

    portfolio_return = calculate_portfolio_return(weights, mean_returns)

    assert portfolio_return == pytest.approx(0.225)


def test_calculate_portfolio_volatility() -> None:
    covariance = pd.DataFrame(
        [
            [0.04, 0.01, 0.02],
            [0.01, 0.09, 0.03],
            [0.02, 0.03, 0.16],
        ],
        columns=["AAPL", "MSFT", "NVDA"],
        index=["AAPL", "MSFT", "NVDA"],
    )
    weights = np.array([0.25, 0.25, 0.50])

    volatility = calculate_portfolio_volatility(weights, covariance)

    assert volatility > 0


def test_calculate_portfolio_sharpe_ratio() -> None:
    sharpe_ratio = calculate_portfolio_sharpe_ratio(
        portfolio_return=0.20,
        portfolio_volatility=0.10,
        risk_free_rate=0.02,
    )

    assert sharpe_ratio == pytest.approx(1.8)


def test_calculate_portfolio_sharpe_ratio_handles_zero_volatility() -> None:
    sharpe_ratio = calculate_portfolio_sharpe_ratio(
        portfolio_return=0.20,
        portfolio_volatility=0.0,
    )

    assert sharpe_ratio == 0.0


def test_build_portfolio_statistics() -> None:
    price_data = build_sample_price_data()
    weights = np.array([1 / 3, 1 / 3, 1 / 3])

    stats = build_portfolio_statistics(price_data, weights)

    assert "asset_returns" in stats
    assert "mean_returns" in stats
    assert "covariance_matrix" in stats
    assert "portfolio_return" in stats
    assert "portfolio_volatility" in stats
    assert "sharpe_ratio" in stats
    assert stats["portfolio_volatility"] >= 0


from portfolio_optimization.optimizers import (
    build_equal_weight_allocations,
    calculate_equal_weight_vector,
    run_equal_weight_optimizer,
    validate_asset_list,
)


def test_validate_asset_list_rejects_empty_list() -> None:
    with pytest.raises(ValueError, match="assets cannot be empty"):
        validate_asset_list([])


def test_validate_asset_list_rejects_single_asset() -> None:
    with pytest.raises(ValueError, match="at least two tickers"):
        validate_asset_list(["AAPL"])


def test_validate_asset_list_rejects_blank_ticker() -> None:
    with pytest.raises(ValueError, match="blank tickers"):
        validate_asset_list(["AAPL", " "])


def test_validate_asset_list_rejects_duplicate_tickers() -> None:
    with pytest.raises(ValueError, match="duplicate tickers"):
        validate_asset_list(["AAPL", "MSFT", "aapl"])


def test_build_equal_weight_allocations() -> None:
    allocations = build_equal_weight_allocations(["aapl", "msft", "nvda", "googl"])

    assert list(allocations.columns) == ["ticker", "weight", "weight_pct"]
    assert list(allocations["ticker"]) == ["AAPL", "MSFT", "NVDA", "GOOGL"]
    assert allocations["weight"].sum() == pytest.approx(1.0)
    assert allocations["weight_pct"].sum() == pytest.approx(100.0)
    assert allocations["weight"].iloc[0] == pytest.approx(0.25)


def test_calculate_equal_weight_vector() -> None:
    weights = calculate_equal_weight_vector(4)

    assert isinstance(weights, np.ndarray)
    assert len(weights) == 4
    assert weights.sum() == pytest.approx(1.0)
    assert weights[0] == pytest.approx(0.25)


def test_calculate_equal_weight_vector_rejects_less_than_two_assets() -> None:
    with pytest.raises(ValueError, match="at least 2"):
        calculate_equal_weight_vector(1)


def test_run_equal_weight_optimizer() -> None:
    price_data = build_sample_price_data()
    result = run_equal_weight_optimizer(price_data)

    assert result["optimizer_name"] == "Equal Weight"
    assert result["assets"] == ["AAPL", "MSFT", "NVDA"]
    assert "weights" in result
    assert "allocations" in result
    assert "portfolio_return" in result
    assert "portfolio_volatility" in result
    assert "sharpe_ratio" in result
    assert result["weights"].sum() == pytest.approx(1.0)
    assert result["portfolio_volatility"] >= 0
