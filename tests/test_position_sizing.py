from __future__ import annotations

import pandas as pd
import pytest

from portfolio_rebalancing.position_sizing import (
    build_position_sizing_summary,
    calculate_position_sizing_table,
    calculate_position_value_cap,
    calculate_risk_based_position_size,
    calculate_risk_budget_amount,
    calculate_stop_loss_dollar_amount,
    validate_position_sizing_inputs,
)


def build_candidate_positions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT", "NVDA"],
            "current_price": [200.0, 400.0, 1000.0],
        }
    )


def test_validate_position_sizing_inputs_accepts_valid_inputs() -> None:
    validate_position_sizing_inputs(
        portfolio_value=10000.0,
        risk_per_trade_pct=1.0,
        stop_loss_pct=5.0,
        current_price=200.0,
        max_position_weight_pct=25.0,
    )


def test_validate_position_sizing_inputs_rejects_bad_values() -> None:
    with pytest.raises(ValueError, match="portfolio_value"):
        validate_position_sizing_inputs(0, 1, 5, 200)

    with pytest.raises(ValueError, match="risk_per_trade_pct"):
        validate_position_sizing_inputs(10000, 0, 5, 200)

    with pytest.raises(ValueError, match="stop_loss_pct"):
        validate_position_sizing_inputs(10000, 1, 0, 200)

    with pytest.raises(ValueError, match="current_price"):
        validate_position_sizing_inputs(10000, 1, 5, 0)

    with pytest.raises(ValueError, match="max_position_weight_pct"):
        validate_position_sizing_inputs(10000, 1, 5, 200, 0)

    with pytest.raises(ValueError, match="cannot be greater than 100"):
        validate_position_sizing_inputs(10000, 1, 5, 200, 101)


def test_calculate_risk_budget_amount() -> None:
    amount = calculate_risk_budget_amount(
        portfolio_value=10000.0,
        risk_per_trade_pct=1.0,
    )

    assert amount == pytest.approx(100.0)


def test_calculate_stop_loss_dollar_amount() -> None:
    amount = calculate_stop_loss_dollar_amount(
        current_price=200.0,
        stop_loss_pct=5.0,
    )

    assert amount == pytest.approx(10.0)


def test_calculate_position_value_cap() -> None:
    cap = calculate_position_value_cap(
        portfolio_value=10000.0,
        max_position_weight_pct=25.0,
    )

    assert cap == pytest.approx(2500.0)


def test_calculate_risk_based_position_size_fractional() -> None:
    result = calculate_risk_based_position_size(
        portfolio_value=10000.0,
        risk_per_trade_pct=1.0,
        stop_loss_pct=5.0,
        current_price=200.0,
        max_position_weight_pct=50.0,
        allow_fractional_shares=True,
    )

    assert result["risk_budget_amount"] == pytest.approx(100.0)
    assert result["stop_loss_dollar_amount"] == pytest.approx(10.0)
    assert result["final_share_quantity"] == pytest.approx(10.0)
    assert result["final_position_value"] == pytest.approx(2000.0)
    assert result["estimated_dollar_risk"] == pytest.approx(100.0)
    assert result["sizing_status"] == "Risk Sized"


def test_calculate_risk_based_position_size_whole_shares() -> None:
    result = calculate_risk_based_position_size(
        portfolio_value=10000.0,
        risk_per_trade_pct=1.0,
        stop_loss_pct=6.0,
        current_price=200.0,
        max_position_weight_pct=50.0,
        allow_fractional_shares=False,
    )

    assert float(result["final_share_quantity"]).is_integer()


def test_calculate_risk_based_position_size_respects_position_cap() -> None:
    result = calculate_risk_based_position_size(
        portfolio_value=10000.0,
        risk_per_trade_pct=5.0,
        stop_loss_pct=5.0,
        current_price=200.0,
        max_position_weight_pct=20.0,
        allow_fractional_shares=True,
    )

    assert result["capped_by_max_weight"] is True
    assert result["final_position_value"] == pytest.approx(2000.0)
    assert result["sizing_status"] == "Capped"


def test_calculate_position_sizing_table() -> None:
    candidates = build_candidate_positions()

    table = calculate_position_sizing_table(
        candidates=candidates,
        portfolio_value=10000.0,
        risk_per_trade_pct=1.0,
        stop_loss_pct=5.0,
        max_position_weight_pct=50.0,
        allow_fractional_shares=True,
    )

    expected_columns = [
        "ticker",
        "current_price",
        "portfolio_value",
        "risk_per_trade_pct",
        "stop_loss_pct",
        "max_position_weight_pct",
        "risk_budget_amount",
        "stop_loss_dollar_amount",
        "final_share_quantity",
        "final_position_value",
        "final_position_weight_pct",
        "estimated_dollar_risk",
        "estimated_risk_pct",
        "capped_by_max_weight",
        "sizing_status",
    ]

    assert list(table.columns) == expected_columns
    assert len(table) == 3
    assert set(table["ticker"]) == {"AAPL", "MSFT", "NVDA"}


def test_calculate_position_sizing_table_rejects_empty_candidates() -> None:
    with pytest.raises(ValueError, match="candidates cannot be empty"):
        calculate_position_sizing_table(
            candidates=pd.DataFrame(),
            portfolio_value=10000.0,
            risk_per_trade_pct=1.0,
            stop_loss_pct=5.0,
        )


def test_calculate_position_sizing_table_rejects_missing_columns() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        calculate_position_sizing_table(
            candidates=pd.DataFrame({"ticker": ["AAPL"]}),
            portfolio_value=10000.0,
            risk_per_trade_pct=1.0,
            stop_loss_pct=5.0,
        )


def test_build_position_sizing_summary() -> None:
    candidates = build_candidate_positions()

    table = calculate_position_sizing_table(
        candidates=candidates,
        portfolio_value=10000.0,
        risk_per_trade_pct=1.0,
        stop_loss_pct=5.0,
        max_position_weight_pct=50.0,
        allow_fractional_shares=True,
    )

    summary = build_position_sizing_summary(table)

    assert summary["candidate_count"] == 3
    assert "total_position_value" in summary
    assert "total_estimated_dollar_risk" in summary
    assert "average_position_weight_pct" in summary
    assert "max_position_weight_pct" in summary
    assert "capped_position_count" in summary
    assert "risk_sized_position_count" in summary


def test_build_position_sizing_summary_rejects_empty_table() -> None:
    with pytest.raises(ValueError, match="position_sizing_table cannot be empty"):
        build_position_sizing_summary(pd.DataFrame())


from portfolio_rebalancing.position_sizing import (
    build_risk_budget_position_sizing_summary,
    calculate_equal_risk_budget_weights,
    calculate_risk_budget_allocations,
    calculate_risk_budget_position_sizing_table,
    validate_risk_budget_weights,
)


def test_validate_risk_budget_weights_accepts_valid_weights() -> None:
    validate_risk_budget_weights(
        risk_budget_weights=[0.25, 0.25, 0.50],
        candidate_count=3,
    )


def test_validate_risk_budget_weights_rejects_bad_length() -> None:
    with pytest.raises(ValueError, match="length"):
        validate_risk_budget_weights(
            risk_budget_weights=[0.50, 0.50],
            candidate_count=3,
        )


def test_validate_risk_budget_weights_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match="negative"):
        validate_risk_budget_weights(
            risk_budget_weights=[0.50, -0.25, 0.75],
            candidate_count=3,
        )


def test_validate_risk_budget_weights_rejects_bad_sum() -> None:
    with pytest.raises(ValueError, match="sum to 1.0"):
        validate_risk_budget_weights(
            risk_budget_weights=[0.30, 0.30, 0.30],
            candidate_count=3,
        )


def test_calculate_equal_risk_budget_weights() -> None:
    weights = calculate_equal_risk_budget_weights(candidate_count=4)

    assert len(weights) == 4
    assert sum(weights) == pytest.approx(1.0)
    assert weights[0] == pytest.approx(0.25)


def test_calculate_equal_risk_budget_weights_rejects_bad_count() -> None:
    with pytest.raises(ValueError, match="candidate_count"):
        calculate_equal_risk_budget_weights(candidate_count=0)


def test_calculate_risk_budget_allocations_equal_weight() -> None:
    candidates = build_candidate_positions()

    allocations = calculate_risk_budget_allocations(
        candidates=candidates,
        total_risk_budget_pct=3.0,
    )

    assert len(allocations) == 3
    assert list(allocations.columns) == [
        "ticker",
        "risk_budget_weight",
        "risk_budget_pct",
    ]
    assert allocations["risk_budget_weight"].sum() == pytest.approx(1.0)
    assert allocations["risk_budget_pct"].sum() == pytest.approx(3.0)


def test_calculate_risk_budget_allocations_custom_weight() -> None:
    candidates = build_candidate_positions()

    allocations = calculate_risk_budget_allocations(
        candidates=candidates,
        total_risk_budget_pct=4.0,
        risk_budget_weights=[0.50, 0.25, 0.25],
    )

    assert allocations["risk_budget_pct"].sum() == pytest.approx(4.0)
    assert allocations.loc[0, "risk_budget_pct"] == pytest.approx(2.0)


def test_calculate_risk_budget_allocations_rejects_bad_budget() -> None:
    candidates = build_candidate_positions()

    with pytest.raises(ValueError, match="total_risk_budget_pct"):
        calculate_risk_budget_allocations(
            candidates=candidates,
            total_risk_budget_pct=0,
        )


def test_calculate_risk_budget_position_sizing_table() -> None:
    candidates = build_candidate_positions()

    table = calculate_risk_budget_position_sizing_table(
        candidates=candidates,
        portfolio_value=10000.0,
        total_risk_budget_pct=3.0,
        stop_loss_pct=5.0,
        max_position_weight_pct=50.0,
        allow_fractional_shares=True,
    )

    expected_columns = [
        "ticker",
        "current_price",
        "portfolio_value",
        "risk_budget_weight",
        "allocated_risk_budget_pct",
        "allocated_risk_budget_amount",
        "stop_loss_pct",
        "max_position_weight_pct",
        "risk_budget_amount",
        "stop_loss_dollar_amount",
        "final_share_quantity",
        "final_position_value",
        "final_position_weight_pct",
        "estimated_dollar_risk",
        "estimated_risk_pct",
        "capped_by_max_weight",
        "sizing_status",
    ]

    assert list(table.columns) == expected_columns
    assert len(table) == 3
    assert table["allocated_risk_budget_pct"].sum() == pytest.approx(3.0)
    assert table["allocated_risk_budget_amount"].sum() == pytest.approx(300.0)


def test_calculate_risk_budget_position_sizing_table_custom_weights() -> None:
    candidates = build_candidate_positions()

    table = calculate_risk_budget_position_sizing_table(
        candidates=candidates,
        portfolio_value=10000.0,
        total_risk_budget_pct=4.0,
        stop_loss_pct=5.0,
        max_position_weight_pct=50.0,
        allow_fractional_shares=True,
        risk_budget_weights=[0.50, 0.25, 0.25],
    )

    assert table.loc[0, "allocated_risk_budget_pct"] == pytest.approx(2.0)
    assert table["allocated_risk_budget_pct"].sum() == pytest.approx(4.0)


def test_build_risk_budget_position_sizing_summary() -> None:
    candidates = build_candidate_positions()

    table = calculate_risk_budget_position_sizing_table(
        candidates=candidates,
        portfolio_value=10000.0,
        total_risk_budget_pct=3.0,
        stop_loss_pct=5.0,
        max_position_weight_pct=50.0,
        allow_fractional_shares=True,
    )

    summary = build_risk_budget_position_sizing_summary(table)

    assert summary["candidate_count"] == 3
    assert summary["total_allocated_risk_budget_pct"] == pytest.approx(3.0)
    assert summary["total_allocated_risk_budget_amount"] == pytest.approx(300.0)
    assert "total_estimated_dollar_risk" in summary
    assert "total_position_value" in summary
    assert "average_position_weight_pct" in summary
    assert "max_position_weight_pct" in summary
    assert "capped_position_count" in summary
    assert "risk_sized_position_count" in summary


def test_build_risk_budget_position_sizing_summary_rejects_empty_table() -> None:
    with pytest.raises(ValueError, match="risk_budget_table cannot be empty"):
        build_risk_budget_position_sizing_summary(pd.DataFrame())
