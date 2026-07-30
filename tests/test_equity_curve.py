from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from paper_trading.equity_curve import (
    add_equity_curve_drawdown_columns,
    add_equity_curve_record,
    build_equity_curve_chart_data,
    build_equity_curve_dataframe,
    build_equity_curve_record,
    build_equity_curve_summary,
    calculate_drawdown_pct,
    calculate_total_account_equity,
    calculate_total_return_pct,
)
from paper_trading.models import ClosedPaperTrade, PaperPosition, PaperTradingAccount


def build_account(cash_balance: float = 8000.0) -> PaperTradingAccount:
    return PaperTradingAccount(
        account_id="acct-1",
        account_name="Test Paper Account",
        starting_cash=10000.0,
        cash_balance=cash_balance,
    )


def build_aapl_position() -> PaperPosition:
    return PaperPosition(
        account_id="acct-1",
        ticker="AAPL",
        quantity=10,
        average_cost=180.0,
        current_price=200.0,
    )


def build_msft_position() -> PaperPosition:
    return PaperPosition(
        account_id="acct-1",
        ticker="MSFT",
        quantity=5,
        average_cost=350.0,
        current_price=400.0,
    )


def build_closed_trade() -> ClosedPaperTrade:
    return ClosedPaperTrade(
        account_id="acct-1",
        ticker="AAPL",
        quantity=2,
        entry_price=180.0,
        exit_price=220.0,
        commission=1.0,
    )


def test_calculate_total_account_equity() -> None:
    result = calculate_total_account_equity(
        cash_balance=8000.0,
        open_positions_market_value=2000.0,
    )

    assert result == pytest.approx(10000.0)


def test_calculate_total_account_equity_rejects_negative_cash() -> None:
    with pytest.raises(ValueError, match="cash_balance"):
        calculate_total_account_equity(
            cash_balance=-1.0,
            open_positions_market_value=2000.0,
        )


def test_calculate_total_return_pct() -> None:
    result = calculate_total_return_pct(
        current_equity=11000.0,
        starting_cash=10000.0,
    )

    assert result == pytest.approx(10.0)


def test_calculate_total_return_pct_rejects_bad_starting_cash() -> None:
    with pytest.raises(ValueError, match="starting_cash"):
        calculate_total_return_pct(
            current_equity=11000.0,
            starting_cash=0.0,
        )


def test_calculate_drawdown_pct() -> None:
    result = calculate_drawdown_pct(
        current_equity=9000.0,
        peak_equity=10000.0,
    )

    assert result == pytest.approx(-10.0)


def test_build_equity_curve_record() -> None:
    record = build_equity_curve_record(
        account=build_account(),
        positions=[build_aapl_position()],
        closed_trades=[build_closed_trade()],
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert record["account_id"] == "acct-1"
    assert record["cash_balance"] == pytest.approx(8000.0)
    assert record["open_positions_market_value"] == pytest.approx(2000.0)
    assert record["total_equity"] == pytest.approx(10000.0)
    assert record["open_position_count"] == 1
    assert record["closed_trade_count"] == 1
    assert record["total_unrealized_pnl"] == pytest.approx(200.0)
    assert record["total_realized_pnl"] == pytest.approx(79.0)


def test_add_equity_curve_record_sorts_records() -> None:
    old_record = {
        "timestamp": datetime(2026, 1, 1, tzinfo=UTC),
        "total_equity": 10000.0,
    }
    new_record = {
        "timestamp": datetime(2026, 1, 2, tzinfo=UTC),
        "total_equity": 10100.0,
    }

    result = add_equity_curve_record([new_record], old_record)

    assert result[0]["timestamp"] == old_record["timestamp"]
    assert result[1]["timestamp"] == new_record["timestamp"]


def test_build_equity_curve_dataframe() -> None:
    record = build_equity_curve_record(
        account=build_account(),
        positions=[build_aapl_position()],
        closed_trades=[],
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )

    df = build_equity_curve_dataframe([record])

    assert len(df) == 1
    assert "total_equity" in df.columns
    assert df.loc[0, "total_equity"] == pytest.approx(10000.0)


def test_add_equity_curve_drawdown_columns() -> None:
    df = pd.DataFrame(
        [
            {"timestamp": datetime(2026, 1, 1, tzinfo=UTC), "total_equity": 10000.0},
            {"timestamp": datetime(2026, 1, 2, tzinfo=UTC), "total_equity": 11000.0},
            {"timestamp": datetime(2026, 1, 3, tzinfo=UTC), "total_equity": 9900.0},
        ]
    )

    result = add_equity_curve_drawdown_columns(df)

    assert result.loc[0, "peak_equity"] == pytest.approx(10000.0)
    assert result.loc[1, "peak_equity"] == pytest.approx(11000.0)
    assert result.loc[2, "drawdown_dollars"] == pytest.approx(-1100.0)
    assert result.loc[2, "drawdown_pct"] == pytest.approx(-10.0)


def test_build_equity_curve_summary() -> None:
    base_time = datetime(2026, 1, 1, tzinfo=UTC)

    records = [
        {
            "timestamp": base_time,
            "account_id": "acct-1",
            "starting_cash": 10000.0,
            "cash_balance": 10000.0,
            "open_positions_market_value": 0.0,
            "total_equity": 10000.0,
            "open_position_count": 0,
            "closed_trade_count": 0,
            "total_unrealized_pnl": 0.0,
            "total_unrealized_pnl_pct": 0.0,
            "total_realized_pnl": 0.0,
            "win_rate_pct": 0.0,
            "total_return_pct": 0.0,
        },
        {
            "timestamp": base_time + timedelta(days=1),
            "account_id": "acct-1",
            "starting_cash": 10000.0,
            "cash_balance": 8500.0,
            "open_positions_market_value": 2500.0,
            "total_equity": 11000.0,
            "open_position_count": 1,
            "closed_trade_count": 0,
            "total_unrealized_pnl": 1000.0,
            "total_unrealized_pnl_pct": 66.6667,
            "total_realized_pnl": 0.0,
            "win_rate_pct": 0.0,
            "total_return_pct": 10.0,
        },
        {
            "timestamp": base_time + timedelta(days=2),
            "account_id": "acct-1",
            "starting_cash": 10000.0,
            "cash_balance": 9000.0,
            "open_positions_market_value": 900.0,
            "total_equity": 9900.0,
            "open_position_count": 1,
            "closed_trade_count": 1,
            "total_unrealized_pnl": -100.0,
            "total_unrealized_pnl_pct": -10.0,
            "total_realized_pnl": 100.0,
            "win_rate_pct": 100.0,
            "total_return_pct": -1.0,
        },
    ]

    summary = build_equity_curve_summary(records)

    assert summary["record_count"] == 3
    assert summary["latest_equity"] == pytest.approx(9900.0)
    assert summary["peak_equity"] == pytest.approx(11000.0)
    assert summary["lowest_equity"] == pytest.approx(9900.0)
    assert summary["total_return_pct"] == pytest.approx(-1.0)
    assert summary["max_drawdown_dollars"] == pytest.approx(-1100.0)
    assert summary["max_drawdown_pct"] == pytest.approx(-10.0)


def test_build_equity_curve_summary_empty() -> None:
    summary = build_equity_curve_summary([])

    assert summary["record_count"] == 0
    assert summary["latest_equity"] == pytest.approx(0.0)


def test_build_equity_curve_chart_data() -> None:
    record = build_equity_curve_record(
        account=build_account(),
        positions=[build_aapl_position(), build_msft_position()],
        closed_trades=[],
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )

    chart_df = build_equity_curve_chart_data([record])

    assert list(chart_df.columns) == [
        "timestamp",
        "total_equity",
        "cash_balance",
        "open_positions_market_value",
        "total_realized_pnl",
        "total_unrealized_pnl",
    ]
    assert len(chart_df) == 1
    assert chart_df.loc[0, "total_equity"] == pytest.approx(12000.0)


def test_build_equity_curve_chart_data_empty() -> None:
    chart_df = build_equity_curve_chart_data([])

    assert chart_df.empty
    assert list(chart_df.columns) == [
        "timestamp",
        "total_equity",
        "cash_balance",
        "open_positions_market_value",
        "total_realized_pnl",
        "total_unrealized_pnl",
    ]
