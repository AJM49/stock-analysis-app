"""Persistence service for rebalance execution audit records."""

import json
from datetime import UTC
from datetime import datetime
from uuid import uuid4

from database import PaperPosition
from database import PaperRebalanceBatch
from database import PaperRebalanceItem
from database import get_database_session


def utc_now():
    """
    Return naive UTC for existing timestamp-without-timezone columns.
    """

    return datetime.now(UTC).replace(tzinfo=None)


BATCH_STATUSES = {
    "PENDING",
    "IN_PROGRESS",
    "COMPLETED",
    "PARTIAL",
    "FAILED",
    "BLOCKED",
}

ITEM_STATUSES = {
    "PENDING",
    "FILLED",
    "FAILED",
    "NOT_EXECUTED",
    "REJECTED",
}


def json_dumps(value):
    """Serialize audit data consistently."""

    if value is None:
        return None

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def json_loads(value, default=None):
    """Deserialize stored audit data safely."""

    if not value:
        return default

    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def create_batch_uid():
    """Create an externally safe rebalance batch identifier."""

    return "RB-" + uuid4().hex[:16].upper()


def capture_portfolio_state(
    account_id,
    cash_balance=None,
):
    """Capture current position quantities for audit comparison."""

    session = get_database_session()

    try:
        positions = (
            session.query(PaperPosition)
            .filter(
                PaperPosition.account_id == int(account_id)
            )
            .order_by(PaperPosition.ticker.asc())
            .all()
        )

        rows = []

        for position in positions:
            rows.append(
                {
                    "position_id": position.id,
                    "ticker": position.ticker,
                    "quantity": float(position.quantity or 0.0),
                    "average_cost": float(
                        position.average_cost or 0.0
                    ),
                    "realized_profit_loss": float(
                        position.realized_profit_loss or 0.0
                    ),
                }
            )

        return {
            "account_id": int(account_id),
            "cash_balance": (
                None
                if cash_balance is None
                else float(cash_balance)
            ),
            "positions": rows,
            "captured_at": utc_now().isoformat(),
        }

    finally:
        session.close()


def create_rebalance_audit_batch(
    account_id,
    approved_candidates,
    target_allocations=None,
    risk_settings=None,
    rebalance_settings=None,
    stop_on_failure=True,
    cash_balance=None,
    estimated_buy_value=0.0,
    estimated_sell_value=0.0,
):
    """Create a batch and its pending item records."""

    candidates = list(approved_candidates or [])

    if not candidates:
        raise ValueError(
            "At least one approved candidate is required."
        )

    session = get_database_session()

    try:
        pre_portfolio = capture_portfolio_state(
            account_id=account_id,
            cash_balance=cash_balance,
        )

        batch = PaperRebalanceBatch(
            batch_uid=create_batch_uid(),
            account_id=int(account_id),
            status="PENDING",
            selected_count=len(candidates),
            filled_count=0,
            failed_count=0,
            unexecuted_count=0,
            stop_on_failure=bool(stop_on_failure),
            estimated_buy_value=float(
                estimated_buy_value or 0.0
            ),
            estimated_sell_value=float(
                estimated_sell_value or 0.0
            ),
            target_allocations_json=json_dumps(
                target_allocations
            ),
            risk_settings_json=json_dumps(
                risk_settings
            ),
            rebalance_settings_json=json_dumps(
                rebalance_settings
            ),
            pre_portfolio_json=json_dumps(
                pre_portfolio
            ),
            created_at=utc_now(),
        )

        session.add(batch)
        session.flush()

        for sequence_number, candidate in enumerate(
            candidates,
            start=1,
        ):
            item = PaperRebalanceItem(
                batch_id=batch.id,
                account_id=int(account_id),
                sequence_number=sequence_number,
                ticker=str(
                    candidate.get("ticker", "")
                ).upper().strip(),
                action=str(
                    candidate.get("action", "")
                ).upper().strip(),
                requested_quantity=float(
                    candidate.get("quantity", 0.0)
                ),
                requested_price=float(
                    candidate.get("execution_price", 0.0)
                ),
                estimated_value=float(
                    candidate.get("estimated_value", 0.0)
                ),
                status="PENDING",
                owned_quantity_before=(
                    candidate.get("owned_quantity")
                ),
                created_at=utc_now(),
            )

            session.add(item)

        session.commit()
        session.refresh(batch)

        return {
            "batch_id": batch.id,
            "batch_uid": batch.batch_uid,
            "status": batch.status,
            "selected_count": batch.selected_count,
        }

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def mark_rebalance_batch_started(batch_id):
    """Mark a pending batch as actively executing."""

    session = get_database_session()

    try:
        batch = (
            session.query(PaperRebalanceBatch)
            .filter(PaperRebalanceBatch.id == int(batch_id))
            .first()
        )

        if batch is None:
            raise ValueError(
                f"Rebalance batch {batch_id} was not found."
            )

        batch.status = "IN_PROGRESS"
        batch.started_at = utc_now()

        session.commit()

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def update_rebalance_item(
    batch_id,
    sequence_number,
    status,
    result=None,
    quantity_after=None,
):
    """Store one item execution outcome."""

    clean_status = str(status).upper().strip()

    if clean_status not in ITEM_STATUSES:
        raise ValueError(
            f"Unsupported rebalance item status: {status}"
        )

    result = result or {}

    session = get_database_session()

    try:
        item = (
            session.query(PaperRebalanceItem)
            .filter(
                PaperRebalanceItem.batch_id == int(batch_id),
                PaperRebalanceItem.sequence_number
                == int(sequence_number),
            )
            .first()
        )

        if item is None:
            raise ValueError(
                "Rebalance item was not found for "
                f"batch {batch_id}, sequence {sequence_number}."
            )

        item.status = clean_status
        item.order_id = result.get("order_id")
        item.trade_id = result.get("trade_id")
        item.cash_balance_after = result.get(
            "cash_balance"
        )
        item.realized_profit_loss = float(
            result.get("realized_profit_loss", 0.0)
            or 0.0
        )
        item.result_message = result.get("message")
        item.quantity_after = quantity_after

        if clean_status in {"FILLED", "FAILED"}:
            item.executed_at = utc_now()

        session.commit()

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def finalize_rebalance_audit_batch(
    batch_id,
    status,
    filled_count,
    failed_count,
    unexecuted_count,
    message,
    cash_balance=None,
):
    """Finalize the batch and capture post-execution state."""

    clean_status = str(status).upper().strip()

    if clean_status not in BATCH_STATUSES:
        raise ValueError(
            f"Unsupported rebalance batch status: {status}"
        )

    session = get_database_session()

    try:
        batch = (
            session.query(PaperRebalanceBatch)
            .filter(PaperRebalanceBatch.id == int(batch_id))
            .first()
        )

        if batch is None:
            raise ValueError(
                f"Rebalance batch {batch_id} was not found."
            )

        post_portfolio = capture_portfolio_state(
            account_id=batch.account_id,
            cash_balance=cash_balance,
        )

        batch.status = clean_status
        batch.filled_count = int(filled_count or 0)
        batch.failed_count = int(failed_count or 0)
        batch.unexecuted_count = int(
            unexecuted_count or 0
        )
        batch.result_message = str(message or "")
        batch.post_portfolio_json = json_dumps(
            post_portfolio
        )
        batch.completed_at = utc_now()

        session.commit()

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


def get_rebalance_batches(account_id, limit=100):
    """Return recent rebalance batches for one account."""

    session = get_database_session()

    try:
        return (
            session.query(PaperRebalanceBatch)
            .filter(
                PaperRebalanceBatch.account_id
                == int(account_id)
            )
            .order_by(
                PaperRebalanceBatch.created_at.desc(),
                PaperRebalanceBatch.id.desc(),
            )
            .limit(int(limit))
            .all()
        )

    finally:
        session.close()


def get_rebalance_batch_items(batch_id):
    """Return ordered audit items for one batch."""

    session = get_database_session()

    try:
        return (
            session.query(PaperRebalanceItem)
            .filter(
                PaperRebalanceItem.batch_id
                == int(batch_id)
            )
            .order_by(
                PaperRebalanceItem.sequence_number.asc()
            )
            .all()
        )

    finally:
        session.close()


def get_rebalance_batch(batch_id, account_id=None):
    """Return one rebalance batch, optionally scoped by account."""

    session = get_database_session()

    try:
        query = (
            session.query(PaperRebalanceBatch)
            .filter(
                PaperRebalanceBatch.id == int(batch_id)
            )
        )

        if account_id is not None:
            query = query.filter(
                PaperRebalanceBatch.account_id
                == int(account_id)
            )

        return query.first()

    finally:
        session.close()

