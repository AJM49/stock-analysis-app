from __future__ import annotations

import pytest

from paper_trading.models import OrderSide, OrderType
from paper_trading.order_preview import (
    build_buy_sell_order_preview,
    build_order_preview_dataframe,
    build_order_preview_reason,
    build_order_preview_summary,
    calculate_portfolio_exposure_pct,
    calculate_position_after_order,
    calculate_position_value_after_order,
    classify_order_preview_status,
)


def test_calculate_position_after_buy_order() -> None:
    result = calculate_position_after_order(
        side=OrderSide.BUY,
        current_position_quantity=5,
        order_quantity=3,
    )

    assert result == pytest.approx(8)


def test_calculate_position_after_sell_order() -> None:
    result = calculate_position_after_order(
        side=OrderSide.SELL,
        current_position_quantity=5,
        order_quantity=3,
    )

    assert result == pytest.approx(2)


def test_calculate_position_after_order_rejects_oversell() -> None:
    with pytest.raises(ValueError, match="sell quantity cannot exceed"):
        calculate_position_after_order(
            side=OrderSide.SELL,
            current_position_quantity=2,
            order_quantity=3,
        )


def test_calculate_position_value_after_order() -> None:
    result = calculate_position_value_after_order(
        position_quantity_after_order=5,
        estimated_price=200.0,
    )

    assert result == pytest.approx(1000.0)


def test_calculate_portfolio_exposure_pct() -> None:
    result = calculate_portfolio_exposure_pct(
        position_value=2500.0,
        portfolio_value=10000.0,
    )

    assert result == pytest.approx(25.0)


def test_classify_order_preview_status() -> None:
    assert classify_order_preview_status(
        is_valid=False,
        exposure_pct_after_order=10.0,
    ) == "Rejected"

    assert classify_order_preview_status(
        is_valid=True,
        exposure_pct_after_order=30.0,
        max_exposure_pct=25.0,
    ) == "Warning"

    assert classify_order_preview_status(
        is_valid=True,
        exposure_pct_after_order=20.0,
        max_exposure_pct=25.0,
    ) == "Accepted"


def test_build_order_preview_reason_rejected() -> None:
    reason = build_order_preview_reason(
        side=OrderSide.BUY,
        preview_status="Rejected",
        ticker="AAPL",
        exposure_pct_after_order=0.0,
        max_exposure_pct=25.0,
        rejection_reason="Insufficient buying power",
    )

    assert reason == "Insufficient buying power"


def test_build_order_preview_reason_warning() -> None:
    reason = build_order_preview_reason(
        side=OrderSide.BUY,
        preview_status="Warning",
        ticker="AAPL",
        exposure_pct_after_order=30.0,
        max_exposure_pct=25.0,
    )

    assert "above the 25.00% max exposure rule" in reason


def test_build_buy_order_preview_accepted() -> None:
    preview = build_buy_sell_order_preview(
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=5,
        order_type=OrderType.MARKET,
        estimated_price=200.0,
        cash_balance=5000.0,
        portfolio_value=10000.0,
        current_position_quantity=0,
        minimum_commission=1.0,
        max_exposure_pct=25.0,
    )

    assert preview["ticker"] == "AAPL"
    assert preview["side"] == "Buy"
    assert preview["estimated_order_value"] == pytest.approx(1000.0)
    assert preview["estimated_cash_after_order"] == pytest.approx(3999.0)
    assert preview["position_quantity_after_order"] == pytest.approx(5)
    assert preview["position_value_after_order"] == pytest.approx(1000.0)
    assert preview["exposure_pct_after_order"] == pytest.approx(10.0)
    assert preview["preview_status"] == "Accepted"


def test_build_buy_order_preview_warning() -> None:
    preview = build_buy_sell_order_preview(
        account_id="acct-1",
        ticker="NVDA",
        side=OrderSide.BUY,
        quantity=4,
        order_type=OrderType.MARKET,
        estimated_price=1000.0,
        cash_balance=10000.0,
        portfolio_value=10000.0,
        current_position_quantity=0,
        max_exposure_pct=25.0,
    )

    assert preview["preview_status"] == "Warning"
    assert preview["exposure_pct_after_order"] == pytest.approx(40.0)


def test_build_buy_order_preview_rejected() -> None:
    preview = build_buy_sell_order_preview(
        account_id="acct-1",
        ticker="NVDA",
        side=OrderSide.BUY,
        quantity=10,
        order_type=OrderType.MARKET,
        estimated_price=1000.0,
        cash_balance=5000.0,
        portfolio_value=10000.0,
        current_position_quantity=0,
        max_exposure_pct=25.0,
    )

    assert preview["preview_status"] == "Rejected"
    assert preview["is_valid"] is False
    assert preview["position_quantity_after_order"] == pytest.approx(0)


def test_build_sell_order_preview_accepted() -> None:
    preview = build_buy_sell_order_preview(
        account_id="acct-1",
        ticker="MSFT",
        side=OrderSide.SELL,
        quantity=2,
        order_type=OrderType.MARKET,
        estimated_price=400.0,
        cash_balance=1000.0,
        portfolio_value=10000.0,
        current_position_quantity=5,
        minimum_commission=1.0,
        max_exposure_pct=25.0,
    )

    assert preview["side"] == "Sell"
    assert preview["estimated_order_value"] == pytest.approx(800.0)
    assert preview["estimated_cash_after_order"] == pytest.approx(1799.0)
    assert preview["position_quantity_after_order"] == pytest.approx(3)
    assert preview["position_value_after_order"] == pytest.approx(1200.0)
    assert preview["preview_status"] == "Accepted"


def test_build_order_preview_dataframe() -> None:
    previews = [
        build_buy_sell_order_preview(
            account_id="acct-1",
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=1,
            order_type=OrderType.MARKET,
            estimated_price=200.0,
            cash_balance=1000.0,
            portfolio_value=10000.0,
        )
    ]

    df = build_order_preview_dataframe(previews)

    assert len(df) == 1
    assert df.loc[0, "ticker"] == "AAPL"


def test_build_order_preview_dataframe_rejects_empty_previews() -> None:
    with pytest.raises(ValueError, match="previews cannot be empty"):
        build_order_preview_dataframe([])


def test_build_order_preview_summary() -> None:
    previews = [
        build_buy_sell_order_preview(
            account_id="acct-1",
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=1,
            order_type=OrderType.MARKET,
            estimated_price=200.0,
            cash_balance=1000.0,
            portfolio_value=10000.0,
        ),
        build_buy_sell_order_preview(
            account_id="acct-1",
            ticker="MSFT",
            side=OrderSide.SELL,
            quantity=1,
            order_type=OrderType.MARKET,
            estimated_price=400.0,
            cash_balance=1000.0,
            portfolio_value=10000.0,
            current_position_quantity=2,
        ),
    ]

    summary = build_order_preview_summary(previews)

    assert summary["preview_count"] == 2
    assert summary["accepted_count"] == 2
    assert summary["buy_count"] == 1
    assert summary["sell_count"] == 1
    assert "total_estimated_order_value" in summary
    assert "max_exposure_pct_after_order" in summary


def test_build_order_preview_summary_rejects_empty_previews() -> None:
    with pytest.raises(ValueError, match="previews cannot be empty"):
        build_order_preview_summary([])
