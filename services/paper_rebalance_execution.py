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
):
    """
    Validate and sequentially execute selected recommendations.

    Each order is sent through execute_market_order(), which
    re-runs paper-order validation and risk controls.
    """

    preview = validate_rebalance_batch(
        account_id=account_id,
        selected_candidates=selected_candidates,
    )

    if not preview["approved"]:
        return {
            "success": False,
            "message": (
                "No valid rebalance recommendations "
                "were selected."
            ),
            "preview": preview,
            "results": [],
            "filled_count": 0,
            "failed_count": preview[
                "rejected_count"
            ],
        }

    if preview["rejected"]:
        return {
            "success": False,
            "message": (
                "Rebalance execution blocked because one or "
                "more selected rows failed validation."
            ),
            "preview": preview,
            "results": [],
            "filled_count": 0,
            "failed_count": preview[
                "rejected_count"
            ],
        }

    results = []
    filled_count = 0
    failed_count = 0

    for candidate in preview["approved"]:
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

        if result["success"]:
            filled_count += 1
        else:
            failed_count += 1

            if stop_on_failure:
                break

    unexecuted_count = (
        len(preview["approved"]) - len(results)
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
    elif filled_count and failed_count:
        message = (
            f"Rebalance batch partially completed: "
            f"{filled_count} filled, "
            f"{failed_count} failed, "
            f"{unexecuted_count} not executed."
        )
    else:
        message = (
            f"Rebalance batch failed: "
            f"{failed_count} order(s) failed, "
            f"{unexecuted_count} not executed."
        )

    return {
        "success": all_filled,
        "message": message,
        "preview": preview,
        "results": results,
        "filled_count": filled_count,
        "failed_count": failed_count,
        "unexecuted_count": unexecuted_count,
    }
