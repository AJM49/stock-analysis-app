from __future__ import annotations

import pytest

from paper_trading.execution_engine import (
    build_execution_summary,
    build_filled_trade,
    execute_paper_order,
    mark_order_filled,
    mark_order_rejected,
    should_fill_order,
    update_account_after_trade,
    update_position_after_buy,
    update_position_after_sell,
    validate_order_for_execution,
)
from paper_trading.models import (
    OrderSide,
    OrderStatus,
    OrderType,
    PaperOrder,
    PaperPosition,
    PaperTrade,
    PaperTradingAccount,
    create_limit_order,
    create_market_order,
)


def build_account() -> PaperTradingAccount:
    return PaperTradingAccount(
        account_id="acct-1",
        account_name="Test Account",
        starting_cash=10000.0,
        cash_balance=10000.0,
    )


def build_position() -> PaperPosition:
    return PaperPosition(
        account_id="acct-1",
        ticker="AAPL",
        quantity=10,
        average_cost=180.0,
        current_price=200.0,
    )


def test_should_fill_market_order() -> None:
    order = create_market_order(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=1,
    )

    assert should_fill_order(order, market_price=200.0) is True


def test_should_fill_limit_buy_order() -> None:
    order = create_limit_order(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=1,
        limit_price=195.0,
    )

    assert should_fill_order(order, market_price=194.0) is True
    assert should_fill_order(order, market_price=196.0) is False


def test_should_fill_limit_sell_order() -> None:
    order = create_limit_order(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.SELL,
        quantity=1,
        limit_price=205.0,
    )

    assert should_fill_order(order, market_price=206.0) is True
    assert should_fill_order(order, market_price=204.0) is False


def test_validate_order_for_execution_accepts_buy() -> None:
    account = build_account()
    order = create_market_order(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=5,
    )

    validate_order_for_execution(
        order=order,
        market_price=200.0,
        account=account,
    )


def test_validate_order_for_execution_rejects_insufficient_cash() -> None:
    account = PaperTradingAccount(
        account_id="acct-1",
        account_name="Test Account",
        starting_cash=1000.0,
        cash_balance=1000.0,
    )

    order = create_market_order(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=10,
    )

    with pytest.raises(ValueError, match="insufficient cash"):
        validate_order_for_execution(
            order=order,
            market_price=200.0,
            account=account,
        )


def test_validate_order_for_execution_rejects_oversell() -> None:
    account = build_account()
    position = build_position()
    order = create_market_order(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.SELL,
        quantity=20,
    )

    with pytest.raises(ValueError, match="sell quantity cannot exceed"):
        validate_order_for_execution(
            order=order,
            market_price=200.0,
            account=account,
            current_position=position,
        )


def test_build_filled_trade() -> None:
    order = create_market_order(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=5,
    )

    trade = build_filled_trade(
        order=order,
        fill_price=200.0,
        commission=1.0,
    )

    assert trade.trade_id
    assert trade.order_id == order.order_id
    assert trade.ticker == "AAPL"
    assert trade.gross_value == pytest.approx(1000.0)
    assert trade.net_cash_impact == pytest.approx(-1001.0)


def test_mark_order_filled() -> None:
    order = create_market_order(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=1,
    )

    updated_order = mark_order_filled(order)

    assert updated_order.status == OrderStatus.FILLED
    assert order.status == OrderStatus.PENDING


def test_mark_order_rejected() -> None:
    order = create_market_order(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=1,
    )

    updated_order = mark_order_rejected(order)

    assert updated_order.status == OrderStatus.REJECTED
    assert order.status == OrderStatus.PENDING


def test_update_account_after_buy_trade() -> None:
    account = build_account()

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

    updated_account = update_account_after_trade(account, trade)

    assert updated_account.cash_balance == pytest.approx(8999.0)


def test_update_account_after_sell_trade() -> None:
    account = build_account()

    trade = PaperTrade(
        trade_id="trade-1",
        order_id="order-1",
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.SELL,
        quantity=5,
        fill_price=200.0,
        commission=1.0,
    )

    updated_account = update_account_after_trade(account, trade)

    assert updated_account.cash_balance == pytest.approx(10999.0)


def test_update_position_after_first_buy() -> None:
    position = update_position_after_buy(
        account_id="acct-1",
        ticker="aapl",
        current_position=None,
        quantity=5,
        fill_price=200.0,
    )

    assert position.ticker == "AAPL"
    assert position.quantity == pytest.approx(5)
    assert position.average_cost == pytest.approx(200.0)


def test_update_position_after_additional_buy() -> None:
    current_position = PaperPosition(
        account_id="acct-1",
        ticker="AAPL",
        quantity=5,
        average_cost=180.0,
        current_price=190.0,
    )

    updated_position = update_position_after_buy(
        account_id="acct-1",
        ticker="AAPL",
        current_position=current_position,
        quantity=5,
        fill_price=200.0,
    )

    assert updated_position.quantity == pytest.approx(10)
    assert updated_position.average_cost == pytest.approx(190.0)


def test_update_position_after_partial_sell() -> None:
    current_position = build_position()

    updated_position, closed_trade = update_position_after_sell(
        current_position=current_position,
        quantity=4,
        fill_price=220.0,
    )

    assert updated_position is not None
    assert updated_position.quantity == pytest.approx(6)
    assert updated_position.average_cost == pytest.approx(180.0)
    assert closed_trade.realized_pnl == pytest.approx(160.0)


def test_update_position_after_full_sell() -> None:
    current_position = build_position()

    updated_position, closed_trade = update_position_after_sell(
        current_position=current_position,
        quantity=10,
        fill_price=220.0,
    )

    assert updated_position is None
    assert closed_trade.realized_pnl == pytest.approx(400.0)


def test_execute_market_buy_order() -> None:
    account = build_account()
    order = create_market_order(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=5,
    )

    result = execute_paper_order(
        order=order,
        account=account,
        market_price=200.0,
        commission=1.0,
    )

    assert result["filled"] is True
    assert result["updated_order"].status == OrderStatus.FILLED
    assert result["trade"].gross_value == pytest.approx(1000.0)
    assert result["updated_account"].cash_balance == pytest.approx(8999.0)
    assert result["updated_position"].quantity == pytest.approx(5)


def test_execute_market_sell_order() -> None:
    account = build_account()
    position = build_position()
    order = create_market_order(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.SELL,
        quantity=5,
    )

    result = execute_paper_order(
        order=order,
        account=account,
        market_price=220.0,
        current_position=position,
        commission=1.0,
    )

    assert result["filled"] is True
    assert result["updated_order"].status == OrderStatus.FILLED
    assert result["updated_account"].cash_balance == pytest.approx(11099.0)
    assert result["updated_position"].quantity == pytest.approx(5)
    assert result["closed_trade"].realized_pnl == pytest.approx(200.0)


def test_execute_limit_order_not_filled() -> None:
    account = build_account()
    order = create_limit_order(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=5,
        limit_price=195.0,
    )

    result = execute_paper_order(
        order=order,
        account=account,
        market_price=200.0,
    )

    assert result["filled"] is False
    assert result["execution_status"] == "Not Filled"
    assert result["updated_order"].status == OrderStatus.PENDING


def test_execute_rejected_buy_order() -> None:
    account = PaperTradingAccount(
        account_id="acct-1",
        account_name="Test Account",
        starting_cash=1000.0,
        cash_balance=1000.0,
    )
    order = create_market_order(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=10,
    )

    result = execute_paper_order(
        order=order,
        account=account,
        market_price=200.0,
    )

    assert result["filled"] is False
    assert result["execution_status"] == "Rejected"
    assert result["updated_order"].status == OrderStatus.REJECTED


def test_build_execution_summary_for_filled_trade() -> None:
    account = build_account()
    order = create_market_order(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=5,
    )

    result = execute_paper_order(
        order=order,
        account=account,
        market_price=200.0,
        commission=1.0,
    )

    summary = build_execution_summary(result)

    assert summary["filled"] is True
    assert summary["execution_status"] == "Filled"
    assert summary["ticker"] == "AAPL"
    assert summary["gross_value"] == pytest.approx(1000.0)
    assert summary["cash_balance_after_trade"] == pytest.approx(8999.0)


def test_build_execution_summary_for_rejected_order() -> None:
    account = PaperTradingAccount(
        account_id="acct-1",
        account_name="Test Account",
        starting_cash=1000.0,
        cash_balance=1000.0,
    )
    order = create_market_order(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=10,
    )

    result = execute_paper_order(
        order=order,
        account=account,
        market_price=200.0,
    )

    summary = build_execution_summary(result)

    assert summary["filled"] is False
    assert summary["execution_status"] == "Rejected"
    assert summary["trade_id"] is None
    assert summary["cash_balance_after_trade"] == pytest.approx(1000.0)
