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


from portfolio_optimization.optimizers import (
    generate_random_weight_matrix,
    run_minimum_volatility_optimizer,
)


def test_generate_random_weight_matrix() -> None:
    weights = generate_random_weight_matrix(
        asset_count=3,
        simulation_count=100,
        random_seed=42,
    )

    assert weights.shape == (100, 3)
    assert np.all(weights >= 0)
    assert np.allclose(weights.sum(axis=1), 1.0)


def test_generate_random_weight_matrix_rejects_single_asset() -> None:
    with pytest.raises(ValueError, match="at least 2"):
        generate_random_weight_matrix(asset_count=1)


def test_generate_random_weight_matrix_rejects_bad_simulation_count() -> None:
    with pytest.raises(ValueError, match="simulation_count"):
        generate_random_weight_matrix(asset_count=3, simulation_count=0)


def test_run_minimum_volatility_optimizer() -> None:
    price_data = build_sample_price_data()

    result = run_minimum_volatility_optimizer(
        price_data=price_data,
        simulation_count=500,
        random_seed=42,
    )

    assert result["optimizer_name"] == "Minimum Volatility"
    assert result["assets"] == ["AAPL", "MSFT", "NVDA"]
    assert "weights" in result
    assert "allocations" in result
    assert "portfolio_return" in result
    assert "portfolio_volatility" in result
    assert "sharpe_ratio" in result
    assert result["simulation_count"] == 500
    assert result["weights"].sum() == pytest.approx(1.0)
    assert np.all(result["weights"] >= 0)
    assert result["portfolio_volatility"] >= 0


def test_minimum_volatility_is_no_worse_than_equal_weight_on_sample_data() -> None:
    price_data = build_sample_price_data()

    equal_weight_result = run_equal_weight_optimizer(price_data)
    minimum_volatility_result = run_minimum_volatility_optimizer(
        price_data=price_data,
        simulation_count=1000,
        random_seed=42,
    )

    assert minimum_volatility_result["portfolio_volatility"] <= (
        equal_weight_result["portfolio_volatility"] + 1e-9
    )


from portfolio_optimization.optimizers import run_maximum_sharpe_optimizer


def test_run_maximum_sharpe_optimizer() -> None:
    price_data = build_sample_price_data()

    result = run_maximum_sharpe_optimizer(
        price_data=price_data,
        simulation_count=500,
        random_seed=42,
    )

    assert result["optimizer_name"] == "Maximum Sharpe"
    assert result["assets"] == ["AAPL", "MSFT", "NVDA"]
    assert "weights" in result
    assert "allocations" in result
    assert "portfolio_return" in result
    assert "portfolio_volatility" in result
    assert "sharpe_ratio" in result
    assert result["simulation_count"] == 500
    assert result["risk_free_rate"] == 0.0
    assert result["weights"].sum() == pytest.approx(1.0)
    assert np.all(result["weights"] >= 0)
    assert result["portfolio_volatility"] >= 0


def test_maximum_sharpe_is_no_worse_than_equal_weight_on_sample_data() -> None:
    price_data = build_sample_price_data()

    equal_weight_result = run_equal_weight_optimizer(price_data)
    maximum_sharpe_result = run_maximum_sharpe_optimizer(
        price_data=price_data,
        simulation_count=1000,
        random_seed=42,
    )

    assert maximum_sharpe_result["sharpe_ratio"] >= (
        equal_weight_result["sharpe_ratio"] - 1e-9
    )


def test_maximum_sharpe_accepts_risk_free_rate() -> None:
    price_data = build_sample_price_data()

    result = run_maximum_sharpe_optimizer(
        price_data=price_data,
        simulation_count=500,
        risk_free_rate=0.02,
        random_seed=42,
    )

    assert result["optimizer_name"] == "Maximum Sharpe"
    assert result["risk_free_rate"] == 0.02
    assert "sharpe_ratio" in result


from portfolio_optimization.comparison import (
    build_allocation_comparison_table,
    build_optimizer_summary_row,
    compare_portfolio_optimizers,
)


def test_build_optimizer_summary_row() -> None:
    price_data = build_sample_price_data()
    result = run_equal_weight_optimizer(price_data)

    row = build_optimizer_summary_row(result)

    assert row["optimizer_name"] == "Equal Weight"
    assert "portfolio_return" in row
    assert "portfolio_return_pct" in row
    assert "portfolio_volatility" in row
    assert "portfolio_volatility_pct" in row
    assert "sharpe_ratio" in row
    assert row["asset_count"] == 3
    assert "allocations" in row
    assert "result" in row


def test_compare_portfolio_optimizers() -> None:
    price_data = build_sample_price_data()

    comparison = compare_portfolio_optimizers(
        price_data=price_data,
        simulation_count=500,
        risk_free_rate=0.0,
        random_seed=42,
    )

    assert "summary" in comparison
    assert "results" in comparison
    assert "best_return_optimizer" in comparison
    assert "lowest_volatility_optimizer" in comparison
    assert "best_sharpe_optimizer" in comparison
    assert comparison["simulation_count"] == 500
    assert comparison["risk_free_rate"] == 0.0
    assert comparison["asset_count"] == 3

    summary = comparison["summary"]

    assert len(summary) == 3
    assert set(summary["optimizer_name"]) == {
        "Equal Weight",
        "Minimum Volatility",
        "Maximum Sharpe",
    }


def test_compare_portfolio_optimizers_rejects_empty_data() -> None:
    with pytest.raises(ValueError, match="price_data cannot be empty"):
        compare_portfolio_optimizers(pd.DataFrame())


def test_build_allocation_comparison_table() -> None:
    price_data = build_sample_price_data()

    comparison = compare_portfolio_optimizers(
        price_data=price_data,
        simulation_count=500,
        random_seed=42,
    )

    allocation_table = build_allocation_comparison_table(comparison)

    assert "ticker" in allocation_table.columns
    assert "Equal Weight" in allocation_table.columns
    assert "Minimum Volatility" in allocation_table.columns
    assert "Maximum Sharpe" in allocation_table.columns
    assert len(allocation_table) == 3
    assert set(allocation_table["ticker"]) == {"AAPL", "MSFT", "NVDA"}


from portfolio_optimization.optimizers import validate_weight_constraints


def test_validate_weight_constraints_accepts_valid_constraints() -> None:
    validate_weight_constraints(
        asset_count=3,
        min_weight=0.05,
        max_weight=0.80,
    )


def test_validate_weight_constraints_rejects_negative_min_weight() -> None:
    with pytest.raises(ValueError, match="min_weight cannot be negative"):
        validate_weight_constraints(
            asset_count=3,
            min_weight=-0.01,
            max_weight=0.80,
        )


def test_validate_weight_constraints_rejects_bad_max_weight() -> None:
    with pytest.raises(ValueError, match="max_weight must be greater than 0"):
        validate_weight_constraints(
            asset_count=3,
            min_weight=0.0,
            max_weight=0.0,
        )


def test_validate_weight_constraints_rejects_min_above_max() -> None:
    with pytest.raises(ValueError, match="min_weight cannot be greater"):
        validate_weight_constraints(
            asset_count=3,
            min_weight=0.50,
            max_weight=0.25,
        )


def test_validate_weight_constraints_rejects_min_too_high() -> None:
    with pytest.raises(ValueError, match="min_weight is too high"):
        validate_weight_constraints(
            asset_count=3,
            min_weight=0.40,
            max_weight=1.0,
        )


def test_validate_weight_constraints_rejects_max_too_low() -> None:
    with pytest.raises(ValueError, match="max_weight is too low"):
        validate_weight_constraints(
            asset_count=3,
            min_weight=0.0,
            max_weight=0.20,
        )


def test_generate_random_weight_matrix_respects_constraints() -> None:
    weights = generate_random_weight_matrix(
        asset_count=3,
        simulation_count=100,
        random_seed=42,
        min_weight=0.10,
        max_weight=0.70,
    )

    assert np.all(weights >= 0.10)
    assert np.all(weights <= 0.70)
    assert np.allclose(weights.sum(axis=1), 1.0)


def test_compare_portfolio_optimizers_accepts_constraints() -> None:
    price_data = build_sample_price_data()

    comparison = compare_portfolio_optimizers(
        price_data=price_data,
        simulation_count=500,
        random_seed=42,
        min_weight=0.05,
        max_weight=0.80,
    )

    assert comparison["min_weight"] == 0.05
    assert comparison["max_weight"] == 0.80
