from __future__ import annotations

import pytest

from paper_trading.models import (
    ClosedPaperTrade,
    OrderSide,
    OrderStatus,
    OrderType,
    PaperOrder,
    PaperPosition,
    PaperTrade,
    PaperTradingAccount,
    TradeJournalEntry,
    create_account,
    create_limit_order,
    create_market_order,
)


def test_create_account() -> None:
    account = create_account(
        account_name="Test Account",
        starting_cash=25000.0,
    )

    assert account.account_id
    assert account.account_name == "Test Account"
    assert account.starting_cash == pytest.approx(25000.0)
    assert account.cash_balance == pytest.approx(25000.0)


def test_account_rejects_bad_cash() -> None:
    with pytest.raises(ValueError, match="starting_cash"):
        PaperTradingAccount(
            account_id="acct-1",
            account_name="Bad Account",
            starting_cash=0,
            cash_balance=0,
        )


def test_create_market_order() -> None:
    order = create_market_order(
        account_id="acct-1",
        ticker="aapl",
        side=OrderSide.BUY,
        quantity=5,
    )

    assert order.order_id
    assert order.ticker == "AAPL"
    assert order.side == OrderSide.BUY
    assert order.quantity == pytest.approx(5)
    assert order.order_type == OrderType.MARKET
    assert order.status == OrderStatus.PENDING


def test_create_limit_order() -> None:
    order = create_limit_order(
        account_id="acct-1",
        ticker="msft",
        side=OrderSide.SELL,
        quantity=2,
        limit_price=400.0,
    )

    assert order.ticker == "MSFT"
    assert order.side == OrderSide.SELL
    assert order.order_type == OrderType.LIMIT
    assert order.limit_price == pytest.approx(400.0)


def test_limit_order_requires_limit_price() -> None:
    with pytest.raises(ValueError, match="limit_price is required"):
        PaperOrder(
            order_id="order-1",
            account_id="acct-1",
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=1,
            order_type=OrderType.LIMIT,
        )


def test_order_rejects_bad_quantity() -> None:
    with pytest.raises(ValueError, match="quantity"):
        create_market_order(
            account_id="acct-1",
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=0,
        )


def test_paper_trade_cash_impact_buy() -> None:
    trade = PaperTrade(
        trade_id="trade-1",
        order_id="order-1",
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=5,
        fill_price=200.0,
        commission=1.0,
    )

    assert trade.gross_value == pytest.approx(1000.0)
    assert trade.net_cash_impact == pytest.approx(-1001.0)


def test_paper_trade_cash_impact_sell() -> None:
    trade = PaperTrade(
        trade_id="trade-2",
        order_id="order-2",
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.SELL,
        quantity=5,
        fill_price=210.0,
        commission=1.0,
    )

    assert trade.gross_value == pytest.approx(1050.0)
    assert trade.net_cash_impact == pytest.approx(1049.0)


def test_paper_position_metrics() -> None:
    position = PaperPosition(
        account_id="acct-1",
        ticker="nvda",
        quantity=2,
        average_cost=900.0,
        current_price=1000.0,
    )

    assert position.ticker == "NVDA"
    assert position.cost_basis == pytest.approx(1800.0)
    assert position.market_value == pytest.approx(2000.0)
    assert position.unrealized_pnl == pytest.approx(200.0)
    assert position.unrealized_pnl_pct == pytest.approx(11.111111, rel=1e-5)


def test_closed_paper_trade_metrics() -> None:
    trade = ClosedPaperTrade(
        account_id="acct-1",
        ticker="AAPL",
        quantity=10,
        entry_price=200.0,
        exit_price=220.0,
        commission=2.0,
    )

    assert trade.realized_pnl == pytest.approx(198.0)
    assert trade.realized_pnl_pct == pytest.approx(9.9)


def test_trade_journal_entry() -> None:
    journal = TradeJournalEntry(
        journal_id="journal-1",
        account_id="acct-1",
        ticker="msft",
        note="Entered because trend and risk rules aligned.",
        linked_trade_id="trade-1",
    )

    assert journal.ticker == "MSFT"
    assert journal.note.startswith("Entered")


def test_trade_journal_rejects_empty_note() -> None:
    with pytest.raises(ValueError, match="note"):
        TradeJournalEntry(
            journal_id="journal-1",
            account_id="acct-1",
            ticker="MSFT",
            note=" ",
        )
