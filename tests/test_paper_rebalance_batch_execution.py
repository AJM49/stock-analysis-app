import services.paper_rebalance_execution as execution


def candidate(ticker, action="BUY", shares=1.0, price=100.0):
    return {
        "Ticker": ticker,
        "Suggested Action": action,
        "Suggested Shares": shares,
        "Current Price": price,
    }


def configure_audit_mocks(monkeypatch):
    updates = []
    finalized = []

    monkeypatch.setattr(
        execution,
        "create_rebalance_audit_batch",
        lambda **kwargs: {
            "batch_id": 101,
            "batch_uid": "RB-TEST-101",
        },
    )

    monkeypatch.setattr(
        execution,
        "mark_rebalance_batch_started",
        lambda batch_id: None,
    )

    monkeypatch.setattr(
        execution,
        "update_rebalance_item",
        lambda **kwargs: updates.append(kwargs),
    )

    monkeypatch.setattr(
        execution,
        "finalize_rebalance_audit_batch",
        lambda **kwargs: finalized.append(kwargs),
    )

    monkeypatch.setattr(
        execution,
        "get_owned_quantity",
        lambda account_id, ticker: 10.0,
    )

    return updates, finalized


def test_successful_multi_order_batch(monkeypatch):
    updates, finalized = configure_audit_mocks(
        monkeypatch
    )

    order_results = iter(
        [
            {
                "success": True,
                "message": "Filled",
                "order_id": 201,
                "trade_id": 301,
                "cash_balance": 900.0,
                "realized_profit_loss": 0.0,
            },
            {
                "success": True,
                "message": "Filled",
                "order_id": 202,
                "trade_id": 302,
                "cash_balance": 800.0,
                "realized_profit_loss": 0.0,
            },
        ]
    )

    monkeypatch.setattr(
        execution,
        "execute_market_order",
        lambda **kwargs: next(order_results),
    )

    result = execution.execute_rebalance_batch(
        account_id=1,
        selected_candidates=[
            candidate("AAPL"),
            candidate("MSFT"),
        ],
        cash_balance=1000.0,
    )

    assert result["success"] is True
    assert result["filled_count"] == 2
    assert result["failed_count"] == 0
    assert result["unexecuted_count"] == 0
    assert result["audit_status"] == "RECORDED"
    assert result["audit_batch_uid"] == "RB-TEST-101"

    assert len(updates) == 2
    assert all(
        update["status"] == "FILLED"
        for update in updates
    )

    assert finalized[0]["status"] == "COMPLETED"
    assert finalized[0]["filled_count"] == 2


def test_stop_on_failure_marks_remaining_unexecuted(
    monkeypatch,
):
    updates, finalized = configure_audit_mocks(
        monkeypatch
    )

    order_results = iter(
        [
            {
                "success": True,
                "message": "Filled",
                "order_id": 201,
                "trade_id": 301,
                "cash_balance": 900.0,
                "realized_profit_loss": 0.0,
            },
            {
                "success": False,
                "message": "Risk check failed",
                "order_id": 202,
                "trade_id": None,
                "cash_balance": 900.0,
                "realized_profit_loss": 0.0,
            },
        ]
    )

    monkeypatch.setattr(
        execution,
        "execute_market_order",
        lambda **kwargs: next(order_results),
    )

    result = execution.execute_rebalance_batch(
        account_id=1,
        selected_candidates=[
            candidate("AAPL"),
            candidate("MSFT"),
            candidate("NVDA"),
        ],
        stop_on_failure=True,
        cash_balance=1000.0,
    )

    assert result["success"] is False
    assert result["filled_count"] == 1
    assert result["failed_count"] == 1
    assert result["unexecuted_count"] == 1

    assert [update["status"] for update in updates] == [
        "FILLED",
        "FAILED",
        "NOT_EXECUTED",
    ]

    assert finalized[0]["status"] == "PARTIAL"
    assert finalized[0]["unexecuted_count"] == 1


def test_continue_after_failure_when_disabled(monkeypatch):
    updates, finalized = configure_audit_mocks(
        monkeypatch
    )

    order_results = iter(
        [
            {
                "success": False,
                "message": "Failed",
                "order_id": 201,
                "trade_id": None,
                "cash_balance": 1000.0,
                "realized_profit_loss": 0.0,
            },
            {
                "success": True,
                "message": "Filled",
                "order_id": 202,
                "trade_id": 302,
                "cash_balance": 900.0,
                "realized_profit_loss": 0.0,
            },
        ]
    )

    monkeypatch.setattr(
        execution,
        "execute_market_order",
        lambda **kwargs: next(order_results),
    )

    result = execution.execute_rebalance_batch(
        account_id=1,
        selected_candidates=[
            candidate("AAPL"),
            candidate("MSFT"),
        ],
        stop_on_failure=False,
    )

    assert result["filled_count"] == 1
    assert result["failed_count"] == 1
    assert result["unexecuted_count"] == 0
    assert finalized[0]["status"] == "PARTIAL"


def test_all_failed_batch_returns_failed_status(monkeypatch):
    updates, finalized = configure_audit_mocks(
        monkeypatch
    )

    monkeypatch.setattr(
        execution,
        "execute_market_order",
        lambda **kwargs: {
            "success": False,
            "message": "Rejected",
            "order_id": 201,
            "trade_id": None,
            "cash_balance": 1000.0,
            "realized_profit_loss": 0.0,
        },
    )

    result = execution.execute_rebalance_batch(
        account_id=1,
        selected_candidates=[
            candidate("AAPL"),
        ],
    )

    assert result["success"] is False
    assert result["filled_count"] == 0
    assert result["failed_count"] == 1
    assert finalized[0]["status"] == "FAILED"
    assert updates[0]["status"] == "FAILED"


def test_audit_creation_failure_does_not_block_order(
    monkeypatch,
):
    monkeypatch.setattr(
        execution,
        "create_rebalance_audit_batch",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("database unavailable")
        ),
    )

    monkeypatch.setattr(
        execution,
        "execute_market_order",
        lambda **kwargs: {
            "success": True,
            "message": "Filled",
            "order_id": 201,
            "trade_id": 301,
            "cash_balance": 900.0,
            "realized_profit_loss": 0.0,
        },
    )

    result = execution.execute_rebalance_batch(
        account_id=1,
        selected_candidates=[
            candidate("AAPL"),
        ],
    )

    assert result["success"] is True
    assert result["filled_count"] == 1
    assert result["audit_status"] == "FAILED"
    assert result["audit_batch_id"] is None
    assert result["audit_errors"]
    assert "creation failed" in (
        result["audit_errors"][0].lower()
    )


def test_audit_finalization_failure_returns_partial(
    monkeypatch,
):
    updates, _ = configure_audit_mocks(monkeypatch)

    monkeypatch.setattr(
        execution,
        "finalize_rebalance_audit_batch",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("finalization unavailable")
        ),
    )

    monkeypatch.setattr(
        execution,
        "execute_market_order",
        lambda **kwargs: {
            "success": True,
            "message": "Filled",
            "order_id": 201,
            "trade_id": 301,
            "cash_balance": 900.0,
            "realized_profit_loss": 0.0,
        },
    )

    result = execution.execute_rebalance_batch(
        account_id=1,
        selected_candidates=[
            candidate("AAPL"),
        ],
    )

    assert result["success"] is True
    assert result["audit_status"] == "PARTIAL"
    assert result["audit_errors"]
    assert len(updates) == 1


def test_validation_failure_places_no_orders(monkeypatch):
    calls = []

    monkeypatch.setattr(
        execution,
        "execute_market_order",
        lambda **kwargs: calls.append(kwargs),
    )

    result = execution.execute_rebalance_batch(
        account_id=1,
        selected_candidates=[
            candidate("AAPL", action="HOLD"),
        ],
    )

    assert result["success"] is False
    assert result["filled_count"] == 0
    assert result["results"] == []
    assert calls == []
    assert result["audit_status"] == "NOT_CREATED"
