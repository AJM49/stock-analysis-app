from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pytest

from database import (
    Base,
    PaperAccount,
    PaperPosition,
    PaperRebalanceBatch,
    PaperRebalanceItem,
)
import services.paper_rebalance_audit as audit


@pytest.fixture
def audit_database(tmp_path, monkeypatch):
    """Provide an isolated database for every audit test."""

    database_path = tmp_path / "audit_test.db"

    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={
            "check_same_thread": False,
        },
    )

    TestSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    Base.metadata.create_all(engine)

    def get_test_session():
        return TestSession()

    monkeypatch.setattr(
        audit,
        "get_database_session",
        get_test_session,
    )

    session = TestSession()

    try:
        account = PaperAccount(
            account_name="Audit Test Account",
            starting_cash=10000.0,
            cash_balance=10000.0,
            is_active=True,
        )

        session.add(account)
        session.flush()

        session.add_all(
            [
                PaperPosition(
                    account_id=account.id,
                    ticker="AAPL",
                    quantity=5.0,
                    average_cost=150.0,
                    realized_profit_loss=0.0,
                ),
                PaperPosition(
                    account_id=account.id,
                    ticker="MSFT",
                    quantity=2.0,
                    average_cost=300.0,
                    realized_profit_loss=25.0,
                ),
            ]
        )

        session.commit()

        account_id = account.id

    finally:
        session.close()

    yield {
        "engine": engine,
        "Session": TestSession,
        "account_id": account_id,
    }

    engine.dispose()


def approved_candidates():
    return [
        {
            "ticker": "AAPL",
            "action": "BUY",
            "quantity": 1.5,
            "execution_price": 200.0,
            "estimated_value": 300.0,
            "owned_quantity": None,
        },
        {
            "ticker": "MSFT",
            "action": "SELL",
            "quantity": 1.0,
            "execution_price": 350.0,
            "estimated_value": 350.0,
            "owned_quantity": 2.0,
        },
    ]


def create_batch(account_id):
    return audit.create_rebalance_audit_batch(
        account_id=account_id,
        approved_candidates=approved_candidates(),
        target_allocations={
            "AAPL": 60.0,
            "MSFT": 30.0,
            "CASH": 10.0,
        },
        risk_settings={
            "maximum_position_pct": 25.0,
        },
        rebalance_settings={
            "drift_rebalance_pct": 5.0,
            "allow_fractional_shares": True,
        },
        stop_on_failure=True,
        cash_balance=10000.0,
        estimated_buy_value=300.0,
        estimated_sell_value=350.0,
    )


def test_json_round_trip_and_invalid_fallback():
    value = {
        "AAPL": 60.0,
        "nested": {
            "enabled": True,
        },
    }

    serialized = audit.json_dumps(value)

    assert audit.json_loads(serialized) == value
    assert audit.json_loads(
        "invalid-json",
        default={},
    ) == {}
    assert audit.json_loads(
        None,
        default=[],
    ) == []


def test_batch_uid_has_expected_format():
    first = audit.create_batch_uid()
    second = audit.create_batch_uid()

    assert first.startswith("RB-")
    assert second.startswith("RB-")
    assert len(first) == 19
    assert first != second


def test_capture_portfolio_state(
    audit_database,
):
    state = audit.capture_portfolio_state(
        account_id=audit_database["account_id"],
        cash_balance=10000.0,
    )

    assert state["account_id"] == (
        audit_database["account_id"]
    )
    assert state["cash_balance"] == 10000.0
    assert len(state["positions"]) == 2

    tickers = [
        position["ticker"]
        for position in state["positions"]
    ]

    assert tickers == ["AAPL", "MSFT"]
    assert state["positions"][0]["quantity"] == 5.0
    assert state["captured_at"]


def test_create_batch_persists_items_and_settings(
    audit_database,
):
    result = create_batch(
        audit_database["account_id"]
    )

    assert result["status"] == "PENDING"
    assert result["selected_count"] == 2
    assert result["batch_uid"].startswith("RB-")

    batch = audit.get_rebalance_batch(
        batch_id=result["batch_id"],
        account_id=audit_database["account_id"],
    )

    items = audit.get_rebalance_batch_items(
        batch_id=result["batch_id"]
    )

    assert batch is not None
    assert batch.status == "PENDING"
    assert batch.selected_count == 2
    assert batch.filled_count == 0
    assert batch.failed_count == 0
    assert batch.unexecuted_count == 0
    assert batch.stop_on_failure is True
    assert batch.estimated_buy_value == 300.0
    assert batch.estimated_sell_value == 350.0

    assert audit.json_loads(
        batch.target_allocations_json
    ) == {
        "AAPL": 60.0,
        "MSFT": 30.0,
        "CASH": 10.0,
    }

    assert audit.json_loads(
        batch.risk_settings_json
    ) == {
        "maximum_position_pct": 25.0,
    }

    assert audit.json_loads(
        batch.rebalance_settings_json
    ) == {
        "allow_fractional_shares": True,
        "drift_rebalance_pct": 5.0,
    }

    pre_portfolio = audit.json_loads(
        batch.pre_portfolio_json
    )

    assert pre_portfolio["cash_balance"] == 10000.0
    assert len(pre_portfolio["positions"]) == 2

    assert len(items) == 2

    assert items[0].sequence_number == 1
    assert items[0].ticker == "AAPL"
    assert items[0].action == "BUY"
    assert items[0].status == "PENDING"
    assert items[0].requested_quantity == 1.5
    assert items[0].estimated_value == 300.0

    assert items[1].sequence_number == 2
    assert items[1].ticker == "MSFT"
    assert items[1].action == "SELL"
    assert items[1].owned_quantity_before == 2.0


def test_batch_start_item_update_and_finalization(
    audit_database,
):
    result = create_batch(
        audit_database["account_id"]
    )

    batch_id = result["batch_id"]

    audit.mark_rebalance_batch_started(batch_id)

    started = audit.get_rebalance_batch(
        batch_id=batch_id
    )

    assert started.status == "IN_PROGRESS"
    assert started.started_at is not None

    audit.update_rebalance_item(
        batch_id=batch_id,
        sequence_number=1,
        status="FILLED",
        result={
            "order_id": 501,
            "trade_id": 601,
            "cash_balance": 9700.0,
            "realized_profit_loss": 0.0,
            "message": "BUY order filled.",
        },
        quantity_after=6.5,
    )

    audit.update_rebalance_item(
        batch_id=batch_id,
        sequence_number=2,
        status="FAILED",
        result={
            "order_id": 502,
            "trade_id": None,
            "cash_balance": 9700.0,
            "realized_profit_loss": 0.0,
            "message": "SELL order rejected.",
        },
        quantity_after=2.0,
    )

    items = audit.get_rebalance_batch_items(batch_id)

    assert items[0].status == "FILLED"
    assert items[0].order_id == 501
    assert items[0].trade_id == 601
    assert items[0].cash_balance_after == 9700.0
    assert items[0].quantity_after == 6.5
    assert items[0].executed_at is not None

    assert items[1].status == "FAILED"
    assert items[1].order_id == 502
    assert items[1].trade_id is None
    assert items[1].quantity_after == 2.0
    assert items[1].executed_at is not None

    audit.finalize_rebalance_audit_batch(
        batch_id=batch_id,
        status="PARTIAL",
        filled_count=1,
        failed_count=1,
        unexecuted_count=0,
        message=(
            "Rebalance batch partially completed."
        ),
        cash_balance=9700.0,
    )

    finalized = audit.get_rebalance_batch(
        batch_id=batch_id
    )

    assert finalized.status == "PARTIAL"
    assert finalized.filled_count == 1
    assert finalized.failed_count == 1
    assert finalized.unexecuted_count == 0
    assert finalized.completed_at is not None
    assert (
        finalized.result_message
        == "Rebalance batch partially completed."
    )

    post_portfolio = audit.json_loads(
        finalized.post_portfolio_json
    )

    assert post_portfolio["cash_balance"] == 9700.0
    assert len(post_portfolio["positions"]) == 2


def test_invalid_statuses_are_rejected(
    audit_database,
):
    result = create_batch(
        audit_database["account_id"]
    )

    with pytest.raises(
        ValueError,
        match="Unsupported rebalance item status",
    ):
        audit.update_rebalance_item(
            batch_id=result["batch_id"],
            sequence_number=1,
            status="UNKNOWN",
        )

    with pytest.raises(
        ValueError,
        match="Unsupported rebalance batch status",
    ):
        audit.finalize_rebalance_audit_batch(
            batch_id=result["batch_id"],
            status="UNKNOWN",
            filled_count=0,
            failed_count=0,
            unexecuted_count=2,
            message="Invalid status test.",
        )


def test_empty_candidate_batch_is_rejected(
    audit_database,
):
    with pytest.raises(
        ValueError,
        match="At least one approved candidate",
    ):
        audit.create_rebalance_audit_batch(
            account_id=audit_database["account_id"],
            approved_candidates=[],
        )


def test_history_queries_are_read_only(
    audit_database,
):
    first = create_batch(
        audit_database["account_id"]
    )
    second = create_batch(
        audit_database["account_id"]
    )

    Session = audit_database["Session"]

    session = Session()

    try:
        batches_before = session.query(
            PaperRebalanceBatch
        ).count()

        items_before = session.query(
            PaperRebalanceItem
        ).count()

    finally:
        session.close()

    batches = audit.get_rebalance_batches(
        account_id=audit_database["account_id"],
        limit=100,
    )

    selected_batch = audit.get_rebalance_batch(
        batch_id=first["batch_id"],
        account_id=audit_database["account_id"],
    )

    selected_items = audit.get_rebalance_batch_items(
        batch_id=second["batch_id"]
    )

    assert len(batches) == 2
    assert selected_batch is not None
    assert len(selected_items) == 2

    session = Session()

    try:
        batches_after = session.query(
            PaperRebalanceBatch
        ).count()

        items_after = session.query(
            PaperRebalanceItem
        ).count()

    finally:
        session.close()

    assert batches_after == batches_before
    assert items_after == items_before


def test_account_scope_prevents_cross_account_lookup(
    audit_database,
):
    result = create_batch(
        audit_database["account_id"]
    )

    batch = audit.get_rebalance_batch(
        batch_id=result["batch_id"],
        account_id=999999,
    )

    assert batch is None
