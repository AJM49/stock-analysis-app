import pandas as pd
import pytest

from services.portfolio_analytics_service import (
    calculate_concentration_diagnostics,
)


def test_equal_weight_four_position_portfolio():
    portfolio_df = pd.DataFrame(
        {
            "Ticker": ["A", "B", "C", "D"],
            "Allocation %": [25.0, 25.0, 25.0, 25.0],
        }
    )

    result = calculate_concentration_diagnostics(
        portfolio_df
    )

    assert result["position_count"] == 4
    assert result["largest_weight_pct"] == 25.0
    assert result["top_3_weight_pct"] == 75.0
    assert result["top_5_weight_pct"] == 100.0
    assert result["hhi"] == pytest.approx(0.25)
    assert result["effective_positions"] == pytest.approx(4.0)
    assert result["diversification_status"] == "Highly Concentrated"


def test_single_position_portfolio_is_maximally_concentrated():
    portfolio_df = pd.DataFrame(
        {
            "Ticker": ["AAPL"],
            "Allocation %": [100.0],
        }
    )

    result = calculate_concentration_diagnostics(
        portfolio_df
    )

    assert result["hhi"] == pytest.approx(1.0)
    assert result["effective_positions"] == pytest.approx(1.0)
    assert result["largest_weight_pct"] == 100.0
    assert result["diversification_status"] == "Highly Concentrated"


def test_ten_equal_positions_are_more_diversified():
    portfolio_df = pd.DataFrame(
        {
            "Ticker": list("ABCDEFGHIJ"),
            "Allocation %": [10.0] * 10,
        }
    )

    result = calculate_concentration_diagnostics(
        portfolio_df
    )

    assert result["hhi"] == pytest.approx(0.10)
    assert result["effective_positions"] == pytest.approx(10.0)
    assert result["top_3_weight_pct"] == pytest.approx(30.0)
    assert result["diversification_status"] == "Moderately Diversified"


def test_empty_portfolio_returns_no_data():
    result = calculate_concentration_diagnostics(
        pd.DataFrame()
    )

    assert result["position_count"] == 0
    assert result["hhi"] == 0.0
    assert result["effective_positions"] == 0.0
    assert result["diversification_status"] == "No Data"


def test_missing_allocation_column_raises():
    portfolio_df = pd.DataFrame(
        {
            "Ticker": ["AAPL"],
        }
    )

    with pytest.raises(
        ValueError,
        match="Allocation %",
    ):
        calculate_concentration_diagnostics(
            portfolio_df
        )



def test_hhi_normalizes_partial_allocation_weights():
    portfolio_df = pd.DataFrame(
        {
            "Ticker": ["A", "B"],
            "Allocation %": [30.0, 30.0],
        }
    )

    result = calculate_concentration_diagnostics(
        portfolio_df
    )

    assert result["hhi"] == pytest.approx(0.5)
    assert result["effective_positions"] == pytest.approx(2.0)



def test_zero_weight_positions_do_not_distort_concentration():
    portfolio_df = pd.DataFrame(
        {
            "Ticker": ["A", "B", "MISSING"],
            "Allocation %": [60.0, 40.0, 0.0],
        }
    )

    result = calculate_concentration_diagnostics(
        portfolio_df
    )

    assert result["position_count"] == 2
    assert result["largest_weight_pct"] == 60.0
    assert result["top_3_weight_pct"] == 100.0
    assert result["hhi"] == pytest.approx(0.52)
    assert result["effective_positions"] == pytest.approx(
        1.0 / 0.52
    )
    assert result["diversification_status"] == "Highly Concentrated"
