from __future__ import annotations

import pytest

from paper_trading.models import (
    OrderSide,
    PaperPosition,
    PaperTrade,
)
from paper_trading.positions_ledger import (
    apply_trade_to_positions,
    build_open_positions_dataframe,
    build_open_positions_summary,
    get_position_by_ticker,
    normalize_ticker,
    update_position_prices,
    upsert_position,
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


def test_normalize_ticker() -> None:
    assert normalize_ticker(" aapl ") == "AAPL"


def test_normalize_ticker_rejects_empty() -> None:
    with pytest.raises(ValueError, match="ticker"):
        normalize_ticker(" ")


def test_get_position_by_ticker_found() -> None:
    positions = [build_aapl_position(), build_msft_position()]

    position = get_position_by_ticker(positions, "aapl")

    assert position is not None
    assert position.ticker == "AAPL"


def test_get_position_by_ticker_missing() -> None:
    positions = [build_aapl_position()]

    position = get_position_by_ticker(positions, "NVDA")

    assert position is None


def test_upsert_position_inserts_new_position() -> None:
    positions = [build_aapl_position()]
    new_position = build_msft_position()

    result = upsert_position(
        positions=positions,
        updated_position=new_position,
        ticker="MSFT",
    )

    assert len(result) == 2
    assert [position.ticker for position in result] == ["AAPL", "MSFT"]


def test_upsert_position_replaces_existing_position() -> None:
    positions = [build_aapl_position()]
    updated_position = PaperPosition(
        account_id="acct-1",
        ticker="AAPL",
        quantity=12,
        average_cost=185.0,
        current_price=205.0,
    )

    result = upsert_position(
        positions=positions,
        updated_position=updated_position,
        ticker="AAPL",
    )

    assert len(result) == 1
    assert result[0].quantity == pytest.approx(12)
    assert result[0].average_cost == pytest.approx(185.0)


def test_upsert_position_removes_closed_position() -> None:
    positions = [build_aapl_position(), build_msft_position()]

    result = upsert_position(
        positions=positions,
        updated_position=None,
        ticker="AAPL",
    )

    assert len(result) == 1
    assert result[0].ticker == "MSFT"


def test_apply_buy_trade_to_empty_positions() -> None:
    trade = PaperTrade(
        trade_id="trade-1",
        order_id="order-1",
        account_id="acct-1",
        ticker="aapl",
        side=OrderSide.BUY,
        quantity=5,
        fill_price=200.0,
    )

    positions, closed_trade = apply_trade_to_positions([], trade)

    assert closed_trade is None
    assert len(positions) == 1
    assert positions[0].ticker == "AAPL"
    assert positions[0].quantity == pytest.approx(5)
    assert positions[0].average_cost == pytest.approx(200.0)


def test_apply_buy_trade_to_existing_position() -> None:
    trade = PaperTrade(
        trade_id="trade-1",
        order_id="order-1",
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=10,
        fill_price=220.0,
    )

    positions, closed_trade = apply_trade_to_positions(
        positions=[build_aapl_position()],
        trade=trade,
    )

    assert closed_trade is None
    assert len(positions) == 1
    assert positions[0].quantity == pytest.approx(20)
    assert positions[0].average_cost == pytest.approx(200.0)


def test_apply_partial_sell_trade() -> None:
    trade = PaperTrade(
        trade_id="trade-1",
        order_id="order-1",
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.SELL,
        quantity=4,
        fill_price=220.0,
    )

    positions, closed_trade = apply_trade_to_positions(
        positions=[build_aapl_position()],
        trade=trade,
    )

    assert len(positions) == 1
    assert positions[0].quantity == pytest.approx(6)
    assert closed_trade is not None
    assert closed_trade.realized_pnl == pytest.approx(160.0)


def test_apply_full_sell_trade_removes_position() -> None:
    trade = PaperTrade(
        trade_id="trade-1",
        order_id="order-1",
        account_id="acct-1",
        ticker="AAPL",
        side=OrderSide.SELL,
        quantity=10,
        fill_price=220.0,
    )

    positions, closed_trade = apply_trade_to_positions(
        positions=[build_aapl_position(), build_msft_position()],
        trade=trade,
    )

    assert len(positions) == 1
    assert positions[0].ticker == "MSFT"
    assert closed_trade is not None
    assert closed_trade.realized_pnl == pytest.approx(400.0)


def test_apply_sell_trade_rejects_missing_position() -> None:
    trade = PaperTrade(
        trade_id="trade-1",
        order_id="order-1",
        account_id="acct-1",
        ticker="NVDA",
        side=OrderSide.SELL,
        quantity=1,
        fill_price=1000.0,
    )

    with pytest.raises(ValueError, match="does not exist"):
        apply_trade_to_positions(
            positions=[build_aapl_position()],
            trade=trade,
        )


def test_build_open_positions_dataframe() -> None:
    positions = [build_aapl_position(), build_msft_position()]

    df = build_open_positions_dataframe(positions)

    assert len(df) == 2
    assert list(df["ticker"]) == ["AAPL", "MSFT"]
    assert "market_value" in df.columns
    assert "unrealized_pnl" in df.columns


def test_build_open_positions_summary() -> None:
    positions = [build_aapl_position(), build_msft_position()]

    summary = build_open_positions_summary(positions)

    assert summary["position_count"] == 2
    assert summary["total_cost_basis"] == pytest.approx(3550.0)
    assert summary["total_market_value"] == pytest.approx(4000.0)
    assert summary["total_unrealized_pnl"] == pytest.approx(450.0)
    assert summary["largest_position_value"] == pytest.approx(2000.0)


def test_build_open_positions_summary_empty() -> None:
    summary = build_open_positions_summary([])

    assert summary["position_count"] == 0
    assert summary["total_market_value"] == pytest.approx(0.0)


def test_update_position_prices() -> None:
    positions = [build_aapl_position(), build_msft_position()]

    updated = update_position_prices(
        positions=positions,
        price_lookup={
            "AAPL": 210.0,
            "MSFT": 390.0,
        },
    )

    assert updated[0].ticker == "AAPL"
    assert updated[0].current_price == pytest.approx(210.0)
    assert updated[1].ticker == "MSFT"
    assert updated[1].current_price == pytest.approx(390.0)


def test_update_position_prices_keeps_missing_prices() -> None:
    positions = [build_aapl_position()]

    updated = update_position_prices(
        positions=positions,
        price_lookup={},
    )

    assert updated[0].current_price == pytest.approx(200.0)


def test_update_position_prices_rejects_bad_price() -> None:
    positions = [build_aapl_position()]

    with pytest.raises(ValueError, match="price_lookup"):
        update_position_prices(
            positions=positions,
            price_lookup={"AAPL": 0.0},
        )
