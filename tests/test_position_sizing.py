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
