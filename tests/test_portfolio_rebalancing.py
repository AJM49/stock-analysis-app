from __future__ import annotations

import pandas as pd
import pytest

from portfolio_rebalancing.rebalancing_math import (
    build_rebalance_summary,
    calculate_current_values,
    calculate_current_weights,
    calculate_rebalance_plan,
    calculate_total_portfolio_value,
    classify_trade_action,
    validate_positions_frame,
)


def build_sample_positions() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT", "NVDA"],
            "shares": [10, 8, 2],
            "current_price": [200.0, 400.0, 1000.0],
            "target_weight": [0.40, 0.35, 0.25],
        }
    )


def test_validate_positions_frame_accepts_valid_positions() -> None:
    positions = build_sample_positions()

    validate_positions_frame(positions)


def test_validate_positions_frame_rejects_empty_positions() -> None:
    with pytest.raises(ValueError, match="positions cannot be empty"):
        validate_positions_frame(pd.DataFrame())


def test_validate_positions_frame_rejects_missing_columns() -> None:
    positions = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "shares": [10],
        }
    )

    with pytest.raises(ValueError, match="missing required columns"):
        validate_positions_frame(positions)


def test_validate_positions_frame_rejects_negative_shares() -> None:
    positions = build_sample_positions()
    positions.loc[0, "shares"] = -1

    with pytest.raises(ValueError, match="shares cannot contain negative"):
        validate_positions_frame(positions)


def test_validate_positions_frame_rejects_bad_price() -> None:
    positions = build_sample_positions()
    positions.loc[0, "current_price"] = 0

    with pytest.raises(ValueError, match="current_price must be greater"):
        validate_positions_frame(positions)


def test_validate_positions_frame_rejects_bad_target_weight_sum() -> None:
    positions = build_sample_positions()
    positions.loc[0, "target_weight"] = 0.10

    with pytest.raises(ValueError, match="target_weight must sum to 1.0"):
        validate_positions_frame(positions)


def test_calculate_current_values() -> None:
    positions = build_sample_positions()
    result = calculate_current_values(positions)

    assert "current_value" in result.columns
    assert result.loc[0, "current_value"] == pytest.approx(2000.0)
    assert result.loc[1, "current_value"] == pytest.approx(3200.0)
    assert result.loc[2, "current_value"] == pytest.approx(2000.0)


def test_calculate_total_portfolio_value() -> None:
    positions = build_sample_positions()

    total_value = calculate_total_portfolio_value(positions)

    assert total_value == pytest.approx(7200.0)


def test_calculate_current_weights() -> None:
    positions = build_sample_positions()
    result = calculate_current_weights(positions)

    assert "current_weight" in result.columns
    assert "current_weight_pct" in result.columns
    assert "target_weight_pct" in result.columns
    assert result["current_weight"].sum() == pytest.approx(1.0)


def test_classify_trade_action() -> None:
    assert classify_trade_action(100.0) == "Buy"
    assert classify_trade_action(-100.0) == "Sell"
    assert classify_trade_action(0.50) == "Hold"


def test_calculate_rebalance_plan() -> None:
    positions = build_sample_positions()
    plan = calculate_rebalance_plan(positions)

    expected_columns = [
        "ticker",
        "shares",
        "current_price",
        "current_value",
        "current_weight",
        "current_weight_pct",
        "target_weight",
        "target_weight_pct",
        "target_value",
        "drift_weight",
        "drift_weight_pct",
        "trade_value",
        "action",
    ]

    assert list(plan.columns) == expected_columns
    assert len(plan) == 3
    assert set(plan["action"]).issubset({"Buy", "Sell", "Hold"})
    assert plan["trade_value"].sum() == pytest.approx(0.0)


def test_build_rebalance_summary() -> None:
    positions = build_sample_positions()
    summary = build_rebalance_summary(positions)

    assert summary["position_count"] == 3
    assert summary["total_portfolio_value"] == pytest.approx(7200.0)
    assert "buy_count" in summary
    assert "sell_count" in summary
    assert "hold_count" in summary
    assert "total_buy_value" in summary
    assert "total_sell_value" in summary
    assert "max_absolute_drift_pct" in summary
    assert "total_absolute_drift_pct" in summary


from portfolio_rebalancing.rebalancing_math import (
    build_allocation_drift_summary,
    calculate_target_vs_current_allocations,
    classify_allocation_drift,
)


def test_classify_allocation_drift() -> None:
    assert classify_allocation_drift(6.0, rebalance_threshold_pct=5.0) == "Rebalance Needed"
    assert classify_allocation_drift(-6.0, rebalance_threshold_pct=5.0) == "Rebalance Needed"
    assert classify_allocation_drift(3.0, rebalance_threshold_pct=5.0) == "Watch"
    assert classify_allocation_drift(1.0, rebalance_threshold_pct=5.0) == "On Target"


def test_calculate_target_vs_current_allocations() -> None:
    positions = build_sample_positions()

    allocation_view = calculate_target_vs_current_allocations(
        positions=positions,
        rebalance_threshold_pct=5.0,
    )

    expected_columns = [
        "ticker",
        "shares",
        "current_price",
        "current_value",
        "current_weight",
        "current_weight_pct",
        "target_weight",
        "target_weight_pct",
        "allocation_drift_pct",
        "absolute_drift_pct",
        "drift_status",
        "needs_rebalance",
    ]

    assert list(allocation_view.columns) == expected_columns
    assert len(allocation_view) == 3
    assert allocation_view["current_weight"].sum() == pytest.approx(1.0)
    assert set(allocation_view["drift_status"]).issubset(
        {"Rebalance Needed", "Watch", "On Target"}
    )
    assert allocation_view["needs_rebalance"].dtype == bool


def test_calculate_target_vs_current_allocations_rejects_bad_threshold() -> None:
    positions = build_sample_positions()

    with pytest.raises(ValueError, match="rebalance_threshold_pct"):
        calculate_target_vs_current_allocations(
            positions=positions,
            rebalance_threshold_pct=0,
        )


def test_build_allocation_drift_summary() -> None:
    positions = build_sample_positions()

    summary = build_allocation_drift_summary(
        positions=positions,
        rebalance_threshold_pct=5.0,
    )

    assert summary["position_count"] == 3
    assert summary["rebalance_threshold_pct"] == 5.0
    assert "positions_needing_rebalance" in summary
    assert "positions_on_watch" in summary
    assert "positions_on_target" in summary
    assert "max_absolute_drift_pct" in summary
    assert "average_absolute_drift_pct" in summary
    assert "total_absolute_drift_pct" in summary
