from __future__ import annotations

from datetime import UTC, datetime

import pytest

from paper_trading.equity_curve import build_equity_curve_record
from paper_trading.models import ClosedPaperTrade, PaperPosition, PaperTradingAccount
from paper_trading.performance_dashboard import (
    build_performance_dashboard_dataframe,
    build_performance_dashboard_metrics,
    build_performance_scorecard,
    build_performance_scorecard_dataframe,
    calculate_average_loss,
    calculate_average_win,
    calculate_expectancy,
    calculate_gross_loss,
    calculate_gross_profit,
    calculate_profit_factor,
    classify_performance_status,
)


def build_account(cash_balance: float = 8000.0) -> PaperTradingAccount:
    return PaperTradingAccount(
        account_id="acct-1",
        account_name="Test Paper Account",
        starting_cash=10000.0,
        cash_balance=cash_balance,
    )


def build_position() -> PaperPosition:
    return PaperPosition(
        account_id="acct-1",
        ticker="AAPL",
        quantity=10,
        average_cost=180.0,
        current_price=200.0,
    )


def build_winning_trade() -> ClosedPaperTrade:
    return ClosedPaperTrade(
        account_id="acct-1",
        ticker="AAPL",
        quantity=5,
        entry_price=180.0,
        exit_price=220.0,
        commission=1.0,
    )


def build_losing_trade() -> ClosedPaperTrade:
    return ClosedPaperTrade(
        account_id="acct-1",
        ticker="MSFT",
        quantity=2,
        entry_price=400.0,
        exit_price=350.0,
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


def test_calculate_average_win() -> None:
    result = calculate_average_win(
        [build_winning_trade(), build_losing_trade()]
    )

    assert result == pytest.approx(199.0)


def test_calculate_average_win_empty() -> None:
    assert calculate_average_win([]) == pytest.approx(0.0)


def test_calculate_average_loss() -> None:
    result = calculate_average_loss(
        [build_winning_trade(), build_losing_trade()]
    )

    assert result == pytest.approx(-101.0)


def test_calculate_average_loss_empty() -> None:
    assert calculate_average_loss([]) == pytest.approx(0.0)


def test_calculate_gross_profit() -> None:
    result = calculate_gross_profit(
        [build_winning_trade(), build_losing_trade()]
    )

    assert result == pytest.approx(199.0)


def test_calculate_gross_loss() -> None:
    result = calculate_gross_loss(
        [build_winning_trade(), build_losing_trade()]
    )

    assert result == pytest.approx(101.0)


def test_calculate_profit_factor() -> None:
    result = calculate_profit_factor(
        [build_winning_trade(), build_losing_trade()]
    )

    assert result == pytest.approx(199.0 / 101.0)


def test_calculate_profit_factor_no_losses() -> None:
    result = calculate_profit_factor([build_winning_trade()])

    assert result == float("inf")


def test_calculate_profit_factor_no_trades() -> None:
    assert calculate_profit_factor([]) == pytest.approx(0.0)


def test_calculate_expectancy() -> None:
    result = calculate_expectancy(
        [build_winning_trade(), build_losing_trade(), build_breakeven_trade()]
    )

    assert result == pytest.approx(32.6666667)


def test_classify_performance_status_strong() -> None:
    result = classify_performance_status(
        total_return_pct=12.0,
        max_drawdown_pct=-3.0,
        profit_factor=2.0,
        win_rate_pct=60.0,
    )

    assert result == "Strong"


def test_classify_performance_status_stable() -> None:
    result = classify_performance_status(
        total_return_pct=1.0,
        max_drawdown_pct=-4.0,
        profit_factor=1.1,
        win_rate_pct=40.0,
    )

    assert result == "Stable"


def test_classify_performance_status_needs_review() -> None:
    result = classify_performance_status(
        total_return_pct=-1.0,
        max_drawdown_pct=-12.0,
        profit_factor=0.8,
        win_rate_pct=40.0,
    )

    assert result == "Needs Review"


def test_build_performance_dashboard_metrics() -> None:
    account = build_account()
    positions = [build_position()]
    closed_trades = [build_winning_trade(), build_losing_trade()]

    equity_record = build_equity_curve_record(
        account=account,
        positions=positions,
        closed_trades=closed_trades,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )

    metrics = build_performance_dashboard_metrics(
        account=account,
        positions=positions,
        closed_trades=closed_trades,
        equity_curve_records=[equity_record],
    )

    assert metrics["account_id"] == "acct-1"
    assert metrics["latest_equity"] == pytest.approx(10000.0)
    assert metrics["open_position_count"] == 1
    assert metrics["closed_trade_count"] == 2
    assert metrics["win_count"] == 1
    assert metrics["loss_count"] == 1
    assert metrics["win_rate_pct"] == pytest.approx(50.0)
    assert metrics["total_realized_pnl"] == pytest.approx(98.0)
    assert metrics["total_unrealized_pnl"] == pytest.approx(200.0)
    assert metrics["average_win"] == pytest.approx(199.0)
    assert metrics["average_loss"] == pytest.approx(-101.0)
    assert metrics["gross_profit"] == pytest.approx(199.0)
    assert metrics["gross_loss"] == pytest.approx(101.0)
    assert metrics["profit_factor"] == pytest.approx(199.0 / 101.0)
    assert "performance_status" in metrics


def test_build_performance_dashboard_metrics_without_equity_records() -> None:
    account = build_account()
    positions = [build_position()]
    closed_trades = []

    metrics = build_performance_dashboard_metrics(
        account=account,
        positions=positions,
        closed_trades=closed_trades,
        equity_curve_records=[],
    )

    assert metrics["latest_equity"] == pytest.approx(10000.0)
    assert metrics["total_return_pct"] == pytest.approx(0.0)
    assert metrics["peak_equity"] == pytest.approx(0.0)
    assert metrics["max_drawdown_pct"] == pytest.approx(0.0)


def test_build_performance_dashboard_dataframe() -> None:
    metrics = {
        "account_id": "acct-1",
        "latest_equity": 10000.0,
        "performance_status": "Stable",
    }

    df = build_performance_dashboard_dataframe(metrics)

    assert len(df) == 1
    assert df.loc[0, "account_id"] == "acct-1"


def test_build_performance_scorecard() -> None:
    metrics = {
        "latest_equity": 10000.0,
        "total_return_pct": 5.0,
        "max_drawdown_pct": -2.0,
        "win_rate_pct": 50.0,
        "profit_factor": 1.5,
        "expectancy": 25.0,
        "total_realized_pnl": 100.0,
        "total_unrealized_pnl": 200.0,
        "performance_status": "Stable",
    }

    scorecard = build_performance_scorecard(metrics)

    assert len(scorecard) == 9
    assert scorecard[0]["metric"] == "Latest Equity"
    assert scorecard[-1]["metric"] == "Performance Status"


def test_build_performance_scorecard_dataframe() -> None:
    metrics = {
        "latest_equity": 10000.0,
        "total_return_pct": 5.0,
        "max_drawdown_pct": -2.0,
        "win_rate_pct": 50.0,
        "profit_factor": 1.5,
        "expectancy": 25.0,
        "total_realized_pnl": 100.0,
        "total_unrealized_pnl": 200.0,
        "performance_status": "Stable",
    }

    df = build_performance_scorecard_dataframe(metrics)

    assert len(df) == 9
    assert list(df.columns) == ["metric", "value", "format", "category"]
