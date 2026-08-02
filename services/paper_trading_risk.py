"""Pre-trade risk controls for simulated paper orders."""

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from math import isfinite

def utc_now():
    """Return naive UTC for existing timestamp columns."""

    return datetime.now(UTC).replace(tzinfo=None)


from database import PaperOrder
from database import PaperPosition


DEFAULT_RISK_SETTINGS = {
    "max_order_value_pct": 10.0,
    "max_position_value_pct": 20.0,
    "minimum_cash_reserve_pct": 10.0,
    "max_share_quantity": 1000.0,
    "duplicate_order_window_seconds": 15,
    "warn_order_value_pct": 7.5,
    "warn_position_value_pct": 15.0,
}

SUPPORTED_SIDES = {"BUY", "SELL"}
BLOCKING_LEVEL = "BLOCK"
WARNING_LEVEL = "WARNING"
PASS_LEVEL = "PASS"

FLOAT_TOLERANCE = 1e-9


def build_risk_result(
    approved,
    message,
    level=PASS_LEVEL,
    violations=None,
    warnings=None,
    metrics=None,
):
    """Return a consistent pre-trade risk result."""

    return {
        "approved": bool(approved),
        "level": str(level),
        "message": str(message),
        "violations": list(violations or []),
        "warnings": list(warnings or []),
        "metrics": dict(metrics or {}),
    }


def validate_finite_number(value, field_name):
    """Validate and convert a numeric risk input."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return False, None, f"{field_name} must be numeric."

    if not isfinite(number):
        return False, None, f"{field_name} must be finite."

    return True, number, None


def normalize_risk_settings(settings=None):
    """Merge supplied settings with safe defaults."""

    normalized = dict(DEFAULT_RISK_SETTINGS)

    if settings:
        normalized.update(settings)

    percentage_fields = [
        "max_order_value_pct",
        "max_position_value_pct",
        "minimum_cash_reserve_pct",
        "warn_order_value_pct",
        "warn_position_value_pct",
    ]

    for field_name in percentage_fields:
        valid, number, error = validate_finite_number(
            normalized.get(field_name),
            field_name,
        )

        if not valid:
            raise ValueError(error)

        if number < 0 or number > 100:
            raise ValueError(
                f"{field_name} must be between 0 and 100."
            )

        normalized[field_name] = number

    valid, max_quantity, error = validate_finite_number(
        normalized.get("max_share_quantity"),
        "max_share_quantity",
    )

    if not valid:
        raise ValueError(error)

    if max_quantity <= 0:
        raise ValueError(
            "max_share_quantity must be greater than zero."
        )

    normalized["max_share_quantity"] = max_quantity

    try:
        duplicate_window = int(
            normalized.get("duplicate_order_window_seconds")
        )
    except (TypeError, ValueError):
        raise ValueError(
            "duplicate_order_window_seconds must be an integer."
        )

    if duplicate_window < 0 or duplicate_window > 3600:
        raise ValueError(
            "duplicate_order_window_seconds must be "
            "between 0 and 3600."
        )

    normalized["duplicate_order_window_seconds"] = duplicate_window

    if (
        normalized["warn_order_value_pct"]
        > normalized["max_order_value_pct"]
    ):
        normalized["warn_order_value_pct"] = normalized[
            "max_order_value_pct"
        ]

    if (
        normalized["warn_position_value_pct"]
        > normalized["max_position_value_pct"]
    ):
        normalized["warn_position_value_pct"] = normalized[
            "max_position_value_pct"
        ]

    return normalized


def calculate_percentage(value, total):
    """Return value as a percentage of total."""

    clean_total = float(total)

    if clean_total <= 0:
        return 0.0

    return float(value) / clean_total * 100.0


def get_existing_position(session, account_id, ticker):
    """Return the existing position for a ticker."""

    return (
        session.query(PaperPosition)
        .filter(
            PaperPosition.account_id == int(account_id),
            PaperPosition.ticker == str(ticker).upper(),
        )
        .first()
    )


def find_recent_duplicate_order(
    session,
    account_id,
    ticker,
    side,
    quantity,
    execution_price,
    window_seconds,
):
    """Return a matching recent order inside the duplicate window."""

    if int(window_seconds) <= 0:
        return None

    cutoff_time = utc_now() - timedelta(
        seconds=int(window_seconds)
    )

    return (
        session.query(PaperOrder)
        .filter(
            PaperOrder.account_id == int(account_id),
            PaperOrder.ticker == str(ticker).upper(),
            PaperOrder.side == str(side).upper(),
            PaperOrder.quantity == float(quantity),
            PaperOrder.requested_price == float(execution_price),
            PaperOrder.submitted_at >= cutoff_time,
            PaperOrder.status.in_(
                [
                    "PENDING",
                    "FILLED",
                ]
            ),
        )
        .order_by(PaperOrder.submitted_at.desc())
        .first()
    )


def evaluate_pre_trade_risk(
    session,
    account,
    ticker,
    side,
    quantity,
    execution_price,
    settings=None,
):
    """
    Evaluate an order before it reaches the transaction engine.

    Blocking controls:
    - maximum share quantity
    - maximum order value
    - maximum resulting position value
    - minimum remaining cash reserve
    - duplicate order submission

    Warning controls:
    - order nearing maximum order allocation
    - position nearing maximum position allocation
    """

    try:
        risk_settings = normalize_risk_settings(settings)
    except ValueError as error:
        return build_risk_result(
            approved=False,
            level=BLOCKING_LEVEL,
            message="Invalid risk settings.",
            violations=[str(error)],
        )

    clean_ticker = str(ticker or "").strip().upper()
    clean_side = str(side or "").strip().upper()

    quantity_valid, clean_quantity, quantity_error = (
        validate_finite_number(
            quantity,
            "Quantity",
        )
    )

    price_valid, clean_price, price_error = (
        validate_finite_number(
            execution_price,
            "Execution price",
        )
    )

    validation_errors = []

    if not clean_ticker:
        validation_errors.append("Ticker cannot be empty.")

    if clean_side not in SUPPORTED_SIDES:
        validation_errors.append(
            "Order side must be BUY or SELL."
        )

    if not quantity_valid:
        validation_errors.append(quantity_error)
    elif clean_quantity <= 0:
        validation_errors.append(
            "Quantity must be greater than zero."
        )

    if not price_valid:
        validation_errors.append(price_error)
    elif clean_price <= 0:
        validation_errors.append(
            "Execution price must be greater than zero."
        )

    if validation_errors:
        return build_risk_result(
            approved=False,
            level=BLOCKING_LEVEL,
            message="Order failed risk input validation.",
            violations=validation_errors,
        )

    starting_cash = float(account.starting_cash)
    cash_balance = float(account.cash_balance)
    order_value = clean_quantity * clean_price

    existing_position = get_existing_position(
        session=session,
        account_id=account.id,
        ticker=clean_ticker,
    )

    existing_quantity = (
        float(existing_position.quantity)
        if existing_position is not None
        else 0.0
    )

    existing_position_value = (
        existing_quantity * clean_price
    )

    if clean_side == "BUY":
        projected_quantity = existing_quantity + clean_quantity
        projected_position_value = (
            projected_quantity * clean_price
        )
        projected_cash = cash_balance - order_value
    else:
        projected_quantity = max(
            existing_quantity - clean_quantity,
            0.0,
        )
        projected_position_value = (
            projected_quantity * clean_price
        )
        projected_cash = cash_balance + order_value

    order_value_pct = calculate_percentage(
        order_value,
        starting_cash,
    )

    projected_position_pct = calculate_percentage(
        projected_position_value,
        starting_cash,
    )

    projected_cash_reserve_pct = calculate_percentage(
        projected_cash,
        starting_cash,
    )

    violations = []
    warnings = []

    if (
        clean_quantity
        > risk_settings["max_share_quantity"]
        + FLOAT_TOLERANCE
    ):
        violations.append(
            "Share quantity exceeds the configured maximum of "
            f'{risk_settings["max_share_quantity"]:g}.'
        )

    if (
        order_value_pct
        > risk_settings["max_order_value_pct"]
        + FLOAT_TOLERANCE
    ):
        violations.append(
            "Order value exceeds the maximum allocation of "
            f'{risk_settings["max_order_value_pct"]:.2f}% '
            "of starting cash."
        )
    elif (
        order_value_pct
        >= risk_settings["warn_order_value_pct"]
        - FLOAT_TOLERANCE
    ):
        warnings.append(
            "Order value is near the configured maximum "
            "order allocation."
        )

    if (
        clean_side == "BUY"
        and projected_position_pct
        > risk_settings["max_position_value_pct"]
        + FLOAT_TOLERANCE
    ):
        violations.append(
            "Projected position exceeds the maximum allocation of "
            f'{risk_settings["max_position_value_pct"]:.2f}% '
            "of starting cash."
        )
    elif (
        clean_side == "BUY"
        and projected_position_pct
        >= risk_settings["warn_position_value_pct"]
        - FLOAT_TOLERANCE
    ):
        warnings.append(
            "Projected position is near the configured maximum "
            "position allocation."
        )

    if (
        clean_side == "BUY"
        and projected_cash_reserve_pct
        + FLOAT_TOLERANCE
        < risk_settings["minimum_cash_reserve_pct"]
    ):
        violations.append(
            "Order would reduce cash below the required reserve of "
            f'{risk_settings["minimum_cash_reserve_pct"]:.2f}% '
            "of starting cash."
        )

    duplicate_order = find_recent_duplicate_order(
        session=session,
        account_id=account.id,
        ticker=clean_ticker,
        side=clean_side,
        quantity=clean_quantity,
        execution_price=clean_price,
        window_seconds=risk_settings[
            "duplicate_order_window_seconds"
        ],
    )

    if duplicate_order is not None:
        violations.append(
            "A matching order was submitted recently. "
            "Wait before submitting it again."
        )

    metrics = {
        "order_value": round(order_value, 2),
        "order_value_pct": round(order_value_pct, 4),
        "existing_position_value": round(
            existing_position_value,
            2,
        ),
        "projected_position_value": round(
            projected_position_value,
            2,
        ),
        "projected_position_pct": round(
            projected_position_pct,
            4,
        ),
        "projected_cash": round(projected_cash, 2),
        "projected_cash_reserve_pct": round(
            projected_cash_reserve_pct,
            4,
        ),
    }

    if violations:
        return build_risk_result(
            approved=False,
            level=BLOCKING_LEVEL,
            message="Order blocked by paper-trading risk controls.",
            violations=violations,
            warnings=warnings,
            metrics=metrics,
        )

    if warnings:
        return build_risk_result(
            approved=True,
            level=WARNING_LEVEL,
            message="Order passed with pre-trade warnings.",
            warnings=warnings,
            metrics=metrics,
        )

    return build_risk_result(
        approved=True,
        level=PASS_LEVEL,
        message="Order passed all pre-trade risk controls.",
        metrics=metrics,
    )
