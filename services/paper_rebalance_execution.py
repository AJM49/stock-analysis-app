"""Guarded execution workflow for rebalance recommendations."""

from math import isfinite

from database import PaperPosition
from database import get_database_session
from services.paper_position_validation import (
    validate_ticker_format,
)
from services.paper_trading_service import (
    execute_market_order,
)
from services.paper_rebalance_audit import (
    create_rebalance_audit_batch,
)
from services.paper_rebalance_audit import (
    finalize_rebalance_audit_batch,
)
from services.paper_rebalance_audit import (
    mark_rebalance_batch_started,
)
from services.paper_rebalance_audit import (
    update_rebalance_item,
)


ALLOWED_ACTIONS = {"BUY", "SELL"}
QUANTITY_PRECISION = 6
MONEY_PRECISION = 2
FLOAT_TOLERANCE = 1e-9


def safe_float(value, default=0.0):
    """Convert a value to a finite float."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(default)

    if not isfinite(number):
        return float(default)

    return number


def normalize_action(value):
    """Normalize a rebalance action."""

    return str(value or "").strip().upper()


def normalize_execution_candidate(candidate):
    """
    Normalize one selected rebalance recommendation.

    Supported keys include both service-style and UI-style names.
    """

    ticker = (
        candidate.get("ticker")
        or candidate.get("Ticker")
    )

    action = (
        candidate.get("suggested_action")
        or candidate.get("Suggested Action")
        or candidate.get("action")
    )

    shares = candidate.get(
        "suggested_share_adjustment",
        candidate.get(
            "Suggested Shares",
            candidate.get("quantity", 0.0),
        ),
    )

    current_price = candidate.get(
        "current_price",
        candidate.get(
            "Current Price",
            candidate.get("execution_price", 0.0),
        ),
    )

    ticker_valid, clean_ticker, ticker_error = (
        validate_ticker_format(ticker)
    )

    if not ticker_valid:
        return {
            "valid": False,
            "error": ticker_error,
            "ticker": clean_ticker,
        }

    clean_action = normalize_action(action)

    if clean_action not in ALLOWED_ACTIONS:
        return {
            "valid": False,
            "error": (
                "Rebalance action must be BUY or SELL."
            ),
            "ticker": clean_ticker,
        }

    raw_shares = safe_float(shares)
    clean_price = round(
        safe_float(current_price),
        MONEY_PRECISION,
    )

    if clean_action == "SELL":
        raw_shares = abs(raw_shares)
    else:
        raw_shares = abs(raw_shares)

    clean_quantity = round(
        raw_shares,
        QUANTITY_PRECISION,
    )

    if clean_quantity <= FLOAT_TOLERANCE:
        return {
            "valid": False,
            "error": (
                "Suggested share quantity must be greater than zero."
            ),
            "ticker": clean_ticker,
        }

    if clean_price <= FLOAT_TOLERANCE:
        return {
            "valid": False,
            "error": (
                "A valid current price is required for execution."
            ),
            "ticker": clean_ticker,
        }

    return {
        "valid": True,
        "error": None,
        "ticker": clean_ticker,
        "action": clean_action,
        "quantity": clean_quantity,
        "execution_price": clean_price,
        "estimated_value": round(
            clean_quantity * clean_price,
            MONEY_PRECISION,
        ),
    }


def get_owned_quantity(account_id, ticker):
    """Return the currently owned quantity for one ticker."""

    session = get_database_session()

    try:
        position = (
            session.query(PaperPosition)
            .filter(
                PaperPosition.account_id == int(account_id),
                PaperPosition.ticker == ticker,
            )
            .first()
        )

        if position is None:
            return 0.0

        return round(
            max(
                safe_float(position.quantity),
                0.0,
            ),
            QUANTITY_PRECISION,
        )

    finally:
        session.close()


def validate_rebalance_batch(
    account_id,
    selected_candidates,
):
    """
    Validate selected recommendations before execution.

    This performs no writes and places no orders.
    """

    normalized = []
    rejected = []
    seen_tickers = set()

    for index, candidate in enumerate(
        selected_candidates or [],
        start=1,
    ):
        result = normalize_execution_candidate(
            candidate
        )

        if not result["valid"]:
            rejected.append(
                {
                    "row": index,
                    "ticker": result.get("ticker"),
                    "error": result["error"],
                }
            )
            continue

        ticker = result["ticker"]

        if ticker in seen_tickers:
            rejected.append(
                {
                    "row": index,
                    "ticker": ticker,
                    "error": (
                        "Duplicate ticker selected in the same "
                        "rebalance batch."
                    ),
                }
            )
            continue

        seen_tickers.add(ticker)

        if result["action"] == "SELL":
            owned_quantity = get_owned_quantity(
                account_id=account_id,
                ticker=ticker,
            )

            if owned_quantity <= FLOAT_TOLERANCE:
                rejected.append(
                    {
                        "row": index,
                        "ticker": ticker,
                        "error": (
                            "SELL recommendation rejected because "
                            "no open shares are owned."
                        ),
                    }
                )
                continue

            if (
                result["quantity"]
                > owned_quantity + FLOAT_TOLERANCE
            ):
                rejected.append(
                    {
                        "row": index,
                        "ticker": ticker,
                        "error": (
                            f"SELL quantity {result['quantity']:g} "
                            f"exceeds owned quantity "
                            f"{owned_quantity:g}."
                        ),
                    }
                )
                continue

            result["owned_quantity"] = (
                owned_quantity
            )
        else:
            result["owned_quantity"] = None

        result["row"] = index
        normalized.append(result)

    estimated_buy_value = round(
        sum(
            row["estimated_value"]
            for row in normalized
            if row["action"] == "BUY"
        ),
        MONEY_PRECISION,
    )

    estimated_sell_value = round(
        sum(
            row["estimated_value"]
            for row in normalized
            if row["action"] == "SELL"
        ),
        MONEY_PRECISION,
    )

    return {
        "valid": len(rejected) == 0 and bool(normalized),
        "approved_count": len(normalized),
        "rejected_count": len(rejected),
        "estimated_buy_value": estimated_buy_value,
        "estimated_sell_value": estimated_sell_value,
        "approved": normalized,
        "rejected": rejected,
    }


def execute_rebalance_batch(
    account_id,
    selected_candidates,
    risk_settings=None,
    stop_on_failure=True,
    target_allocations=None,
    rebalance_settings=None,
    cash_balance=None,
):
    """
    Validate and sequentially execute selected recommendations.

    Each order is sent through execute_market_order(), which
    re-runs paper-order validation and risk controls.

    Audit persistence is best-effort. Audit errors are returned
    explicitly but do not suppress valid paper-order execution.
    """

    preview = validate_rebalance_batch(
        account_id=account_id,
        selected_candidates=selected_candidates,
    )

    base_result = {
        "preview": preview,
        "results": [],
        "filled_count": 0,
        "failed_count": 0,
        "unexecuted_count": 0,
        "audit_batch_id": None,
        "audit_batch_uid": None,
        "audit_status": "NOT_CREATED",
        "audit_errors": [],
    }

    if not preview["approved"]:
        base_result.update(
            {
                "success": False,
                "message": (
                    "No valid rebalance recommendations "
                    "were selected."
                ),
                "failed_count": preview[
                    "rejected_count"
                ],
            }
        )
        return base_result

    if preview["rejected"]:
        base_result.update(
            {
                "success": False,
                "message": (
                    "Rebalance execution blocked because one or "
                    "more selected rows failed validation."
                ),
                "failed_count": preview[
                    "rejected_count"
                ],
            }
        )
        return base_result

    audit_batch_id = None
    audit_batch_uid = None
    audit_errors = []

    try:
        audit = create_rebalance_audit_batch(
            account_id=account_id,
            approved_candidates=preview["approved"],
            target_allocations=target_allocations,
            risk_settings=risk_settings,
            rebalance_settings=rebalance_settings,
            stop_on_failure=stop_on_failure,
            cash_balance=cash_balance,
            estimated_buy_value=preview[
                "estimated_buy_value"
            ],
            estimated_sell_value=preview[
                "estimated_sell_value"
            ],
        )

        audit_batch_id = audit["batch_id"]
        audit_batch_uid = audit["batch_uid"]

    except Exception as error:
        audit_errors.append(
            "Audit batch creation failed: "
            + str(error)
        )

    if audit_batch_id is not None:
        try:
            mark_rebalance_batch_started(
                audit_batch_id
            )
        except Exception as error:
            audit_errors.append(
                "Audit batch start update failed: "
                + str(error)
            )

    results = []
    filled_count = 0
    failed_count = 0
    latest_cash_balance = cash_balance

    for sequence_number, candidate in enumerate(
        preview["approved"],
        start=1,
    ):
        result = execute_market_order(
            account_id=account_id,
            ticker=candidate["ticker"],
            side=candidate["action"],
            quantity=candidate["quantity"],
            execution_price=(
                candidate["execution_price"]
            ),
            risk_settings=risk_settings,
        )

        execution_result = {
            "sequence_number": sequence_number,
            "ticker": candidate["ticker"],
            "action": candidate["action"],
            "quantity": candidate["quantity"],
            "execution_price": (
                candidate["execution_price"]
            ),
            "estimated_value": (
                candidate["estimated_value"]
            ),
            "success": bool(result["success"]),
            "message": result["message"],
            "order_id": result.get("order_id"),
            "trade_id": result.get("trade_id"),
            "cash_balance": result.get(
                "cash_balance"
            ),
            "realized_profit_loss": result.get(
                "realized_profit_loss",
                0.0,
            ),
        }

        results.append(execution_result)

        if result.get("cash_balance") is not None:
            latest_cash_balance = result.get(
                "cash_balance"
            )

        if result["success"]:
            filled_count += 1
            item_status = "FILLED"
        else:
            failed_count += 1
            item_status = "FAILED"

        if audit_batch_id is not None:
            try:
                quantity_after = get_owned_quantity(
                    account_id=account_id,
                    ticker=candidate["ticker"],
                )

                update_rebalance_item(
                    batch_id=audit_batch_id,
                    sequence_number=sequence_number,
                    status=item_status,
                    result=execution_result,
                    quantity_after=quantity_after,
                )

            except Exception as error:
                audit_errors.append(
                    "Audit item update failed for "
                    f'{candidate["ticker"]}: {error}'
                )

        if (
            not result["success"]
            and stop_on_failure
        ):
            break

    unexecuted_count = (
        len(preview["approved"]) - len(results)
    )

    if (
        audit_batch_id is not None
        and unexecuted_count > 0
    ):
        first_unexecuted_sequence = (
            len(results) + 1
        )

        for sequence_number in range(
            first_unexecuted_sequence,
            len(preview["approved"]) + 1,
        ):
            candidate = preview["approved"][
                sequence_number - 1
            ]

            try:
                update_rebalance_item(
                    batch_id=audit_batch_id,
                    sequence_number=sequence_number,
                    status="NOT_EXECUTED",
                    result={
                        "message": (
                            "Not executed because the "
                            "rebalance batch stopped after "
                            "an earlier failure."
                        ),
                    },
                    quantity_after=get_owned_quantity(
                        account_id=account_id,
                        ticker=candidate["ticker"],
                    ),
                )

            except Exception as error:
                audit_errors.append(
                    "Audit unexecuted-item update failed for "
                    f'{candidate["ticker"]}: {error}'
                )

    all_filled = (
        filled_count == len(preview["approved"])
        and failed_count == 0
    )

    if all_filled:
        message = (
            f"Rebalance batch completed: "
            f"{filled_count} order(s) filled."
        )
        final_audit_status = "COMPLETED"

    elif filled_count and (
        failed_count or unexecuted_count
    ):
        message = (
            f"Rebalance batch partially completed: "
            f"{filled_count} filled, "
            f"{failed_count} failed, "
            f"{unexecuted_count} not executed."
        )
        final_audit_status = "PARTIAL"

    else:
        message = (
            f"Rebalance batch failed: "
            f"{failed_count} order(s) failed, "
            f"{unexecuted_count} not executed."
        )
        final_audit_status = "FAILED"

    audit_status = "NOT_CREATED"

    if audit_batch_id is not None:
        try:
            finalize_rebalance_audit_batch(
                batch_id=audit_batch_id,
                status=final_audit_status,
                filled_count=filled_count,
                failed_count=failed_count,
                unexecuted_count=unexecuted_count,
                message=message,
                cash_balance=latest_cash_balance,
            )

            audit_status = "RECORDED"

        except Exception as error:
            audit_errors.append(
                "Audit batch finalization failed: "
                + str(error)
            )
            audit_status = "PARTIAL"

    elif audit_errors:
        audit_status = "FAILED"

    return {
        "success": all_filled,
        "message": message,
        "preview": preview,
        "results": results,
        "filled_count": filled_count,
        "failed_count": failed_count,
        "unexecuted_count": unexecuted_count,
        "audit_batch_id": audit_batch_id,
        "audit_batch_uid": audit_batch_uid,
        "audit_status": audit_status,
        "audit_errors": audit_errors,
    }

