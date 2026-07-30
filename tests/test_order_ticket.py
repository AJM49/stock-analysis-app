from __future__ import annotations

import pytest

from paper_trading.models import OrderSide, OrderType
from paper_trading.order_ticket import (
    build_order_preview_table_row,
    build_order_ticket,
    calculate_cash_impact,
    calculate_estimated_order_value,
    calculate_order_commission,
    check_buying_power,
    estimate_order_price,
    serialize_order,
    validate_order_ticket_inputs,
)


def test_validate_order_ticket_inputs_accepts_valid_market_order() -> None:
    validate_order_ticket_inputs(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=5,
        order_type=OrderType.MARKET,
        estimated_price=200.0,
        cash_balance=5000.0,
    )


def test_validate_order_ticket_inputs_rejects_empty_ticker() -> None:
    with pytest.raises(ValueError, match="ticker"):
        validate_order_ticket_inputs(
            account_id="acct-1",
            ticker=" ",
            side=OrderSide.BUY,
            quantity=5,
            order_type=OrderType.MARKET,
            estimated_price=200.0,
        )


def test_validate_order_ticket_inputs_rejects_bad_quantity() -> None:
    with pytest.raises(ValueError, match="quantity"):
        validate_order_ticket_inputs(
            account_id="acct-1",
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=0,
            order_type=OrderType.MARKET,
            estimated_price=200.0,
        )


def test_validate_order_ticket_inputs_rejects_limit_without_price() -> None:
    with pytest.raises(ValueError, match="limit_price is required"):
        validate_order_ticket_inputs(
            account_id="acct-1",
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=1,
            order_type=OrderType.LIMIT,
            estimated_price=200.0,
        )


def test_validate_order_ticket_inputs_rejects_oversell() -> None:
    with pytest.raises(ValueError, match="sell quantity cannot exceed"):
        validate_order_ticket_inputs(
            account_id="acct-1",
            ticker="AAPL",
            side=OrderSide.SELL,
            quantity=10,
            order_type=OrderType.MARKET,
            estimated_price=200.0,
            current_position_quantity=5,
        )


def test_estimate_order_price_market() -> None:
    assert estimate_order_price(
        order_type=OrderType.MARKET,
        estimated_price=200.0,
    ) == pytest.approx(200.0)


def test_estimate_order_price_limit() -> None:
    assert estimate_order_price(
        order_type=OrderType.LIMIT,
        estimated_price=200.0,
        limit_price=195.0,
    ) == pytest.approx(195.0)


def test_calculate_estimated_order_value() -> None:
    value = calculate_estimated_order_value(
        quantity=5,
        order_price=200.0,
    )

    assert value == pytest.approx(1000.0)


def test_calculate_order_commission_uses_percentage() -> None:
    commission = calculate_order_commission(
        order_value=1000.0,
        commission_rate_pct=0.25,
        minimum_commission=1.0,
    )

    assert commission == pytest.approx(2.5)


def test_calculate_order_commission_uses_minimum() -> None:
    commission = calculate_order_commission(
        order_value=100.0,
        commission_rate_pct=0.25,
        minimum_commission=1.0,
    )

    assert commission == pytest.approx(1.0)


def test_calculate_cash_impact_buy() -> None:
    cash_impact = calculate_cash_impact(
        side=OrderSide.BUY,
        order_value=1000.0,
        commission=1.0,
    )

    assert cash_impact == pytest.approx(-1001.0)


def test_calculate_cash_impact_sell() -> None:
    cash_impact = calculate_cash_impact(
        side=OrderSide.SELL,
        order_value=1000.0,
        commission=1.0,
    )

    assert cash_impact == pytest.approx(999.0)


def test_check_buying_power_for_buy_true() -> None:
    assert check_buying_power(
        side=OrderSide.BUY,
        cash_balance=2000.0,
        order_value=1000.0,
        commission=1.0,
    ) is True


def test_check_buying_power_for_buy_false() -> None:
    assert check_buying_power(
        side=OrderSide.BUY,
        cash_balance=500.0,
        order_value=1000.0,
        commission=1.0,
    ) is False


def test_check_buying_power_for_sell_true() -> None:
    assert check_buying_power(
        side=OrderSide.SELL,
        cash_balance=0.0,
        order_value=1000.0,
        commission=1.0,
    ) is True


def test_build_order_ticket_market_buy() -> None:
    ticket = build_order_ticket(
        account_id="acct-1",
        ticker="aapl",
        side=OrderSide.BUY,
        quantity=5,
        order_type=OrderType.MARKET,
        estimated_price=200.0,
        cash_balance=5000.0,
        commission_rate_pct=0.0,
        minimum_commission=1.0,
    )

    assert ticket["ticker"] == "AAPL"
    assert ticket["side"] == "Buy"
    assert ticket["order_type"] == "Market"
    assert ticket["estimated_order_value"] == pytest.approx(1000.0)
    assert ticket["estimated_commission"] == pytest.approx(1.0)
    assert ticket["estimated_cash_impact"] == pytest.approx(-1001.0)
    assert ticket["estimated_cash_after_order"] == pytest.approx(3999.0)
    assert ticket["has_buying_power"] is True
    assert ticket["is_valid"] is True


def test_build_order_ticket_limit_sell() -> None:
    ticket = build_order_ticket(
        account_id="acct-1",
        ticker="MSFT",
        side=OrderSide.SELL,
        quantity=2,
        order_type=OrderType.LIMIT,
        estimated_price=400.0,
        limit_price=410.0,
        cash_balance=1000.0,
        current_position_quantity=5.0,
        commission_rate_pct=0.0,
        minimum_commission=1.0,
    )

    assert ticket["ticker"] == "MSFT"
    assert ticket["side"] == "Sell"
    assert ticket["order_type"] == "Limit"
    assert ticket["order_price"] == pytest.approx(410.0)
    assert ticket["estimated_order_value"] == pytest.approx(820.0)
    assert ticket["estimated_cash_impact"] == pytest.approx(819.0)
    assert ticket["estimated_cash_after_order"] == pytest.approx(1819.0)


def test_build_order_ticket_insufficient_buying_power() -> None:
    ticket = build_order_ticket(
        account_id="acct-1",
        ticker="NVDA",
        side=OrderSide.BUY,
        quantity=10,
        order_type=OrderType.MARKET,
        estimated_price=1000.0,
        cash_balance=5000.0,
    )

    assert ticket["has_buying_power"] is False
    assert ticket["is_valid"] is False
    assert ticket["rejection_reason"] == "Insufficient buying power"


def test_build_order_preview_table_row() -> None:
    ticket = build_order_ticket(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=1,
        order_type=OrderType.MARKET,
        estimated_price=200.0,
        cash_balance=1000.0,
    )

    row = build_order_preview_table_row(ticket)

    assert row["ticker"] == "AAPL"
    assert row["side"] == "Buy"
    assert row["estimated_order_value"] == pytest.approx(200.0)
    assert row["is_valid"] is True


def test_serialize_order() -> None:
    ticket = build_order_ticket(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=1,
        order_type=OrderType.MARKET,
        estimated_price=200.0,
    )

    serialized = serialize_order(ticket["order"])

    assert serialized["ticker"] == "AAPL"
    assert serialized["side"] == "Buy"
    assert serialized["order_type"] == "Market"
    assert serialized["status"] == "Pending"
