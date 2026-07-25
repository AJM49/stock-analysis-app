from __future__ import annotations

import pandas as pd

from risk.risk_metrics import (
    build_risk_metric_summary,
    calculate_annualized_return,
    calculate_annualized_volatility,
    calculate_daily_returns,
    calculate_drawdown_duration,
    calculate_max_drawdown_pct,
    calculate_rolling_volatility,
    calculate_sharpe_ratio,
    calculate_value_at_risk,
)


def build_sample_equity_curve() -> pd.DataFrame:
    """Create a sample equity curve with gains and drawdowns."""
    return pd.DataFrame(
        {
            "Date": pd.date_range("2026-01-01", periods=10, freq="D"),
            "total_value": [
                10_000,
                10_200,
                10_100,
                10_500,
                10_300,
                10_700,
                10_600,
                10_900,
                10_800,
                11_000,
            ],
        }
    )


def test_calculate_daily_returns() -> None:
    equity_curve = build_sample_equity_curve()
    returns = calculate_daily_returns(equity_curve)

    assert len(returns) == len(equity_curve)
    assert returns.iloc[0] == 0.0


def test_calculate_annualized_return() -> None:
    equity_curve = build_sample_equity_curve()
    result = calculate_annualized_return(equity_curve)

    assert isinstance(result, float)


def test_calculate_annualized_volatility() -> None:
    equity_curve = build_sample_equity_curve()
    result = calculate_annualized_volatility(equity_curve)

    assert isinstance(result, float)
    assert result >= 0


def test_calculate_sharpe_ratio() -> None:
    equity_curve = build_sample_equity_curve()
    result = calculate_sharpe_ratio(equity_curve)

    assert isinstance(result, float)


def test_calculate_max_drawdown_pct() -> None:
    equity_curve = build_sample_equity_curve()
    result = calculate_max_drawdown_pct(equity_curve)

    assert isinstance(result, float)
    assert result <= 0


def test_calculate_drawdown_duration() -> None:
    equity_curve = build_sample_equity_curve()
    result = calculate_drawdown_duration(equity_curve)

    assert isinstance(result, int)
    assert result >= 0


def test_calculate_value_at_risk() -> None:
    equity_curve = build_sample_equity_curve()
    result = calculate_value_at_risk(equity_curve)

    assert isinstance(result, float)


def test_build_risk_metric_summary() -> None:
    equity_curve = build_sample_equity_curve()
    result = build_risk_metric_summary(equity_curve)

    expected_keys = {
        "annualized_return_pct",
        "annualized_volatility_pct",
        "sharpe_ratio",
        "sortino_ratio",
        "max_drawdown_pct",
        "drawdown_duration",
        "value_at_risk_95_pct",
        "conditional_value_at_risk_95_pct",
        "calmar_ratio",
    }

    assert expected_keys.issubset(result.keys())


def test_calculate_rolling_volatility() -> None:
    equity_curve = build_sample_equity_curve()
    result = calculate_rolling_volatility(equity_curve, window=3)

    assert "rolling_volatility_3" in result.columns
    assert len(result) == len(equity_curve)
    assert result["rolling_volatility_3"].notna().all()
