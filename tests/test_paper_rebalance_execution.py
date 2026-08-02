import pytest

import services.paper_rebalance_execution as execution


def candidate(
    ticker="AAPL",
    action="BUY",
    shares=1.0,
    price=100.0,
):
    return {
        "Ticker": ticker,
        "Suggested Action": action,
        "Suggested Shares": shares,
        "Current Price": price,
    }


def test_normalize_valid_buy_candidate():
    result = execution.normalize_execution_candidate(
        candidate(
            ticker="aapl",
            action="buy",
            shares=2.5,
            price=100,
        )
    )

    assert result["valid"] is True
    assert result["ticker"] == "AAPL"
    assert result["action"] == "BUY"
    assert result["quantity"] == 2.5
    assert result["execution_price"] == 100.0
    assert result["estimated_value"] == 250.0


def test_normalize_valid_sell_uses_absolute_quantity():
    result = execution.normalize_execution_candidate(
        candidate(
            action="SELL",
            shares=-2,
            price=50,
        )
    )

    assert result["valid"] is True
    assert result["action"] == "SELL"
    assert result["quantity"] == 2.0
    assert result["estimated_value"] == 100.0


@pytest.mark.parametrize(
    "action",
    [
        "HOLD",
        "",
        None,
        "WAIT",
    ],
)
def test_non_executable_actions_are_rejected(action):
    result = execution.normalize_execution_candidate(
        candidate(action=action)
    )

    assert result["valid"] is False
    assert "BUY or SELL" in result["error"]


@pytest.mark.parametrize(
    "quantity",
    [
        0,
        None,
        "invalid",
    ],
)
def test_nonpositive_quantity_is_rejected(quantity):
    result = execution.normalize_execution_candidate(
        candidate(shares=quantity)
    )

    assert result["valid"] is False
    assert "greater than zero" in result["error"]


@pytest.mark.parametrize(
    "price",
    [
        0,
        -1,
        None,
        "invalid",
    ],
)
def test_invalid_execution_price_is_rejected(price):
    result = execution.normalize_execution_candidate(
        candidate(price=price)
    )

    assert result["valid"] is False
    assert "valid current price" in result["error"]


def test_duplicate_ticker_blocks_batch(monkeypatch):
    monkeypatch.setattr(
        execution,
        "get_owned_quantity",
        lambda account_id, ticker: 100.0,
    )

    result = execution.validate_rebalance_batch(
        account_id=1,
        selected_candidates=[
            candidate(
                ticker="AAPL",
                action="BUY",
            ),
            candidate(
                ticker="aapl",
                action="SELL",
            ),
        ],
    )

    assert result["valid"] is False
    assert result["approved_count"] == 1
    assert result["rejected_count"] == 1
    assert "Duplicate ticker" in (
        result["rejected"][0]["error"]
    )


def test_sell_without_owned_shares_is_rejected(
    monkeypatch,
):
    monkeypatch.setattr(
        execution,
        "get_owned_quantity",
        lambda account_id, ticker: 0.0,
    )

    result = execution.validate_rebalance_batch(
        account_id=1,
        selected_candidates=[
            candidate(
                ticker="AAPL",
                action="SELL",
                shares=1,
            )
        ],
    )

    assert result["valid"] is False
    assert result["approved_count"] == 0
    assert result["rejected_count"] == 1
    assert "no open shares" in (
        result["rejected"][0]["error"]
    )


def test_sell_over_owned_quantity_is_rejected(
    monkeypatch,
):
    monkeypatch.setattr(
        execution,
        "get_owned_quantity",
        lambda account_id, ticker: 2.0,
    )

    result = execution.validate_rebalance_batch(
        account_id=1,
        selected_candidates=[
            candidate(
                ticker="AAPL",
                action="SELL",
                shares=3,
            )
        ],
    )

    assert result["valid"] is False
    assert "exceeds owned quantity" in (
        result["rejected"][0]["error"]
    )


def test_valid_sell_batch_is_approved(monkeypatch):
    monkeypatch.setattr(
        execution,
        "get_owned_quantity",
        lambda account_id, ticker: 5.0,
    )

    result = execution.validate_rebalance_batch(
        account_id=1,
        selected_candidates=[
            candidate(
                ticker="AAPL",
                action="SELL",
                shares=2,
                price=150,
            )
        ],
    )

    assert result["valid"] is True
    assert result["approved_count"] == 1
    assert result["rejected_count"] == 0
    assert result["estimated_sell_value"] == 300.0
    assert result["approved"][0][
        "owned_quantity"
    ] == 5.0


def test_valid_buy_batch_calculates_total():
    result = execution.validate_rebalance_batch(
        account_id=1,
        selected_candidates=[
            candidate(
                ticker="AAPL",
                action="BUY",
                shares=2,
                price=100,
            ),
            candidate(
                ticker="MSFT",
                action="BUY",
                shares=1.5,
                price=200,
            ),
        ],
    )

    assert result["valid"] is True
    assert result["approved_count"] == 2
    assert result["estimated_buy_value"] == 500.0
    assert result["estimated_sell_value"] == 0.0


def test_empty_batch_is_invalid():
    result = execution.validate_rebalance_batch(
        account_id=1,
        selected_candidates=[],
    )

    assert result["valid"] is False
    assert result["approved_count"] == 0
    assert result["rejected_count"] == 0
