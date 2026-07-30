from __future__ import annotations

import pytest

from paper_trading.closed_trades_ledger import (
    add_closed_trade,
    build_closed_trades_dataframe,
    build_closed_trades_summary,
    calculate_closed_trade_entry_value,
    calculate_closed_trade_exit_value,
    calculate_realized_pnl_by_ticker,
    classify_closed_trade_result,
    get_closed_trades_by_ticker,
    normalize_ticker,
)
from paper_trading.models import ClosedPaperTrade


def build_winning_trade() -> ClosedPaperTrade:
    return ClosedPaperTrade(
        account_id="acct-1",
        ticker="AAPL",
        quantity=10,
        entry_price=200.0,
        exit_price=220.0,
        commission=2.0,
    )


def build_losing_trade() -> ClosedPaperTrade:
    return ClosedPaperTrade(
        account_id="acct-1",
        ticker="MSFT",
        quantity=5,
        entry_price=400.0,
        exit_price=380.0,
        commission=1.0,
    )


def build_breakeven_trade() -> ClosedPaperTrade:
    return ClosedPaperTrade(
        account_id="acct-1",
        ticker="NVDA",
        quantity=1,
        entry_price=1000.0,
        exit_price=1000.0,
        commission=0.0,
    )


def test_normalize_ticker() -> None:
    assert normalize_ticker(" aapl ") == "AAPL"


def test_normalize_ticker_rejects_empty() -> None:
    with pytest.raises(ValueError, match="ticker"):
        normalize_ticker(" ")


def test_classify_closed_trade_result() -> None:
    assert classify_closed_trade_result(build_winning_trade()) == "Win"
    assert classify_closed_trade_result(build_losing_trade()) == "Loss"
    assert classify_closed_trade_result(build_breakeven_trade()) == "Breakeven"


def test_add_closed_trade() -> None:
    trades = [build_winning_trade()]
    result = add_closed_trade(trades, build_losing_trade())

    assert len(result) == 2
    assert {trade.ticker for trade in result} == {"AAPL", "MSFT"}


def test_get_closed_trades_by_ticker() -> None:
    trades = [
        build_winning_trade(),
        build_losing_trade(),
        build_breakeven_trade(),
    ]

    result = get_closed_trades_by_ticker(trades, "aapl")

    assert len(result) == 1
    assert result[0].ticker == "AAPL"


def test_get_closed_trades_by_ticker_missing() -> None:
    trades = [build_winning_trade()]

    result = get_closed_trades_by_ticker(trades, "MSFT")

    assert result == []


def test_calculate_closed_trade_entry_value() -> None:
    trade = build_winning_trade()

    assert calculate_closed_trade_entry_value(trade) == pytest.approx(2000.0)


def test_calculate_closed_trade_exit_value() -> None:
    trade = build_winning_trade()

    assert calculate_closed_trade_exit_value(trade) == pytest.approx(2200.0)


def test_build_closed_trades_dataframe() -> None:
    trades = [
        build_winning_trade(),
        build_losing_trade(),
        build_breakeven_trade(),
    ]

    df = build_closed_trades_dataframe(trades)

    expected_columns = [
        "account_id",
        "ticker",
        "quantity",
        "entry_price",
        "exit_price",
        "entry_value",
        "exit_value",
        "commission",
        "realized_pnl",
        "realized_pnl_pct",
        "result",
        "closed_at",
    ]

    assert list(df.columns) == expected_columns
    assert len(df) == 3
    assert set(df["result"]) == {"Win", "Loss", "Breakeven"}


def test_build_closed_trades_summary() -> None:
    trades = [
        build_winning_trade(),
        build_losing_trade(),
        build_breakeven_trade(),
    ]

    summary = build_closed_trades_summary(trades)

    assert summary["closed_trade_count"] == 3
    assert summary["win_count"] == 1
    assert summary["loss_count"] == 1
    assert summary["breakeven_count"] == 1
    assert summary["win_rate_pct"] == pytest.approx(33.333333, rel=1e-5)
    assert summary["total_realized_pnl"] == pytest.approx(97.0)
    assert summary["best_trade_ticker"] == "AAPL"
    assert summary["worst_trade_ticker"] == "MSFT"


def test_build_closed_trades_summary_empty() -> None:
    summary = build_closed_trades_summary([])

    assert summary["closed_trade_count"] == 0
    assert summary["win_rate_pct"] == pytest.approx(0.0)
    assert summary["best_trade_ticker"] is None


def test_calculate_realized_pnl_by_ticker() -> None:
    trades = [
        build_winning_trade(),
        build_losing_trade(),
        build_breakeven_trade(),
        ClosedPaperTrade(
            account_id="acct-1",
            ticker="AAPL",
            quantity=5,
            entry_price=210.0,
            exit_price=230.0,
            commission=1.0,
        ),
    ]

    result = calculate_realized_pnl_by_ticker(trades)

    expected_columns = [
        "ticker",
        "closed_trade_count",
        "total_realized_pnl",
        "average_realized_pnl",
        "average_realized_pnl_pct",
        "win_count",
        "loss_count",
        "win_rate_pct",
    ]

    assert list(result.columns) == expected_columns
    assert len(result) == 3
    assert result.loc[0, "ticker"] == "AAPL"
    assert result.loc[0, "closed_trade_count"] == 2
    assert result.loc[0, "total_realized_pnl"] == pytest.approx(297.0)


def test_calculate_realized_pnl_by_ticker_empty() -> None:
    result = calculate_realized_pnl_by_ticker([])

    assert result.empty
    assert list(result.columns) == [
        "ticker",
        "closed_trade_count",
        "total_realized_pnl",
        "average_realized_pnl",
        "average_realized_pnl_pct",
        "win_count",
        "loss_count",
        "win_rate_pct",
    ]
