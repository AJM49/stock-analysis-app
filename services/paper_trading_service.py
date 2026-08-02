"""Paper-trading order validation and execution service."""

from datetime import UTC
from datetime import datetime
from math import isfinite

def utc_now():
    """Return naive UTC for existing timestamp columns."""

    return datetime.now(UTC).replace(tzinfo=None)


from database import PaperAccount
from database import PaperOrder
from database import PaperPosition
from database import PaperTrade
from database import get_database_session
from services.paper_trading_risk import evaluate_pre_trade_risk
from services.paper_trading_performance import save_automatic_equity_snapshot
from services.paper_position_validation import validate_ticker_format


VALID_ORDER_SIDES = {"BUY", "SELL"}
MARKET_ORDER_TYPE = "MARKET"
FILLED_STATUS = "FILLED"
REJECTED_STATUS = "REJECTED"

MONEY_PRECISION = 2
QUANTITY_PRECISION = 6
FLOAT_TOLERANCE = 1e-9


def normalize_ticker(ticker):
    """Return a normalized stock ticker."""

    return str(ticker or "").strip().upper()


def normalize_side(side):
    """Return a normalized order side."""

    return str(side or "").strip().upper()


def validate_positive_number(value, field_name):
    """Validate and convert a numeric input."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return False, None, field_name + " must be numeric."

    if not isfinite(number):
        return False, None, field_name + " must be finite."

    if number <= 0:
        return False, None, field_name + " must be greater than zero."

    return True, number, None


def validate_order_inputs(ticker, side, quantity, execution_price):
    """Validate common paper-order inputs."""

    clean_ticker = normalize_ticker(ticker)
    clean_side = normalize_side(side)

    ticker_valid, clean_ticker, ticker_error = (
        validate_ticker_format(clean_ticker)
    )

    if not ticker_valid:
        return False, None, ticker_error

    if clean_side not in VALID_ORDER_SIDES:
        return False, None, "Order side must be BUY or SELL."

    quantity_valid, clean_quantity, quantity_error = validate_positive_number(
        quantity,
        "Quantity",
    )

    if not quantity_valid:
        return False, None, quantity_error

    price_valid, clean_price, price_error = validate_positive_number(
        execution_price,
        "Execution price",
    )

    if not price_valid:
        return False, None, price_error

    clean_quantity = round(clean_quantity, QUANTITY_PRECISION)
    clean_price = round(clean_price, MONEY_PRECISION)

    if clean_quantity <= 0:
        return False, None, "Quantity is too small after rounding."

    if clean_price <= 0:
        return False, None, "Execution price is too small after rounding."

    return (
        True,
        {
            "ticker": clean_ticker,
            "side": clean_side,
            "quantity": clean_quantity,
            "execution_price": clean_price,
        },
        None,
    )


def build_order_result(
    success,
    message,
    order=None,
    trade=None,
    position=None,
    account=None,
):
    """Build a consistent response for the UI and tests."""

    return {
        "success": bool(success),
        "message": str(message),
        "order_id": getattr(order, "id", None),
        "trade_id": getattr(trade, "id", None),
        "position_id": getattr(position, "id", None),
        "account_id": getattr(account, "id", None),
        "cash_balance": (
            round(float(account.cash_balance), MONEY_PRECISION)
            if account is not None
            else None
        ),
        "ticker": getattr(order, "ticker", None),
        "side": getattr(order, "side", None),
        "quantity": (
            round(float(order.quantity), QUANTITY_PRECISION)
            if order is not None
            else None
        ),
        "execution_price": (
            round(float(order.executed_price), MONEY_PRECISION)
            if order is not None and order.executed_price is not None
            else None
        ),
        "order_value": (
            round(float(order.order_value), MONEY_PRECISION)
            if order is not None and order.order_value is not None
            else None
        ),
        "realized_profit_loss": (
            round(float(trade.realized_profit_loss), MONEY_PRECISION)
            if trade is not None
            else 0.0
        ),
    }


def create_rejected_order(
    session,
    account_id,
    ticker,
    side,
    quantity,
    execution_price,
    reason,
):
    """Persist a rejected order for audit history."""

    clean_ticker = normalize_ticker(ticker)
    clean_side = normalize_side(side)

    try:
        clean_quantity = float(quantity)
    except (TypeError, ValueError):
        clean_quantity = 0.0

    try:
        clean_price = float(execution_price)
    except (TypeError, ValueError):
        clean_price = None

    rejected_order = PaperOrder(
        account_id=int(account_id),
        ticker=clean_ticker or "UNKNOWN",
        side=clean_side or "UNKNOWN",
        order_type=MARKET_ORDER_TYPE,
        quantity=max(clean_quantity, 0.0),
        requested_price=clean_price,
        executed_price=None,
        order_value=None,
        status=REJECTED_STATUS,
        rejection_reason=str(reason),
        submitted_at=utc_now(),
        executed_at=None,
    )

    session.add(rejected_order)
    session.commit()
    session.refresh(rejected_order)

    return rejected_order


def get_account_for_execution(session, account_id):
    """Load an active paper account for an order."""

    return (
        session.query(PaperAccount)
        .filter(
            PaperAccount.id == int(account_id),
            PaperAccount.is_active.is_(True),
        )
        .first()
    )


def get_position_for_execution(session, account_id, ticker):
    """Load a paper position for an account and ticker."""

    return (
        session.query(PaperPosition)
        .filter(
            PaperPosition.account_id == int(account_id),
            PaperPosition.ticker == ticker,
        )
        .first()
    )


def execute_buy_order(
    session,
    account,
    ticker,
    quantity,
    execution_price,
):
    """Execute a simulated market buy."""

    order_value = round(quantity * execution_price, MONEY_PRECISION)

    if order_value > float(account.cash_balance) + FLOAT_TOLERANCE:
        raise ValueError(
            "Insufficient cash. "
            f"Required ${order_value:,.2f}; "
            f"available ${float(account.cash_balance):,.2f}."
        )

    position = get_position_for_execution(
        session=session,
        account_id=account.id,
        ticker=ticker,
    )

    if position is None:
        position = PaperPosition(
            account_id=account.id,
            ticker=ticker,
            quantity=quantity,
            average_cost=execution_price,
            realized_profit_loss=0.0,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(position)
    else:
        old_quantity = float(position.quantity)
        old_average_cost = float(position.average_cost)
        new_quantity = round(
            old_quantity + quantity,
            QUANTITY_PRECISION,
        )

        new_total_cost = (
            old_quantity * old_average_cost
            + quantity * execution_price
        )

        position.quantity = new_quantity
        position.average_cost = round(
            new_total_cost / new_quantity,
            MONEY_PRECISION,
        )
        position.updated_at = utc_now()

    account.cash_balance = round(
        float(account.cash_balance) - order_value,
        MONEY_PRECISION,
    )
    account.updated_at = utc_now()

    return position, order_value, 0.0


def execute_sell_order(
    session,
    account,
    ticker,
    quantity,
    execution_price,
):
    """Execute a simulated market sell."""

    position = get_position_for_execution(
        session=session,
        account_id=account.id,
        ticker=ticker,
    )

    if position is None:
        raise ValueError(
            "Sell rejected because no open position exists for "
            + ticker
            + "."
        )

    owned_quantity = float(position.quantity)

    if quantity > owned_quantity + FLOAT_TOLERANCE:
        raise ValueError(
            "Insufficient shares. "
            f"Requested {quantity:g}; owned {owned_quantity:g}."
        )

    order_value = round(quantity * execution_price, MONEY_PRECISION)
    realized_profit_loss = round(
        quantity * (execution_price - float(position.average_cost)),
        MONEY_PRECISION,
    )

    remaining_quantity = round(
        owned_quantity - quantity,
        QUANTITY_PRECISION,
    )

    position.realized_profit_loss = round(
        float(position.realized_profit_loss or 0.0)
        + realized_profit_loss,
        MONEY_PRECISION,
    )
    position.updated_at = utc_now()

    if remaining_quantity <= FLOAT_TOLERANCE:
        position.quantity = 0.0
        position.average_cost = 0.0
    else:
        position.quantity = remaining_quantity

    account.cash_balance = round(
        float(account.cash_balance) + order_value,
        MONEY_PRECISION,
    )
    account.updated_at = utc_now()

    return position, order_value, realized_profit_loss


def execute_market_order(
    account_id,
    ticker,
    side,
    quantity,
    execution_price,
    risk_settings=None,
):
    """
    Validate and execute a simulated market order atomically.

    The transaction updates:
    - paper account cash
    - paper position quantity and average cost
    - paper order history
    - paper trade history
    """

    session = get_database_session()

    try:
        account = get_account_for_execution(
            session=session,
            account_id=account_id,
        )

        if account is None:
            return build_order_result(
                success=False,
                message="Active paper account was not found.",
            )

        valid, clean_order, validation_error = validate_order_inputs(
            ticker=ticker,
            side=side,
            quantity=quantity,
            execution_price=execution_price,
        )

        if not valid:
            rejected_order = create_rejected_order(
                session=session,
                account_id=account.id,
                ticker=ticker,
                side=side,
                quantity=quantity,
                execution_price=execution_price,
                reason=validation_error,
            )

            return build_order_result(
                success=False,
                message=validation_error,
                order=rejected_order,
                account=account,
            )

        clean_ticker = clean_order["ticker"]
        clean_side = clean_order["side"]
        clean_quantity = clean_order["quantity"]
        clean_price = clean_order["execution_price"]

        risk_result = evaluate_pre_trade_risk(
            session=session,
            account=account,
            ticker=clean_ticker,
            side=clean_side,
            quantity=clean_quantity,
            execution_price=clean_price,
            settings=risk_settings,
        )

        risk_warning_message = ""

        if not risk_result["approved"]:
            rejection_reasons = risk_result.get(
                "violations",
                [],
            )

            rejection_reason = "; ".join(rejection_reasons)

            if not rejection_reason:
                rejection_reason = risk_result.get(
                    "message",
                    "Order blocked by risk controls.",
                )

            rejected_order = create_rejected_order(
                session=session,
                account_id=account.id,
                ticker=clean_ticker,
                side=clean_side,
                quantity=clean_quantity,
                execution_price=clean_price,
                reason=rejection_reason,
            )

            return build_order_result(
                success=False,
                message=(
                    risk_result.get(
                        "message",
                        "Order blocked by risk controls.",
                    )
                    + " "
                    + rejection_reason
                ).strip(),
                order=rejected_order,
                account=account,
            )

        risk_warnings = risk_result.get("warnings", [])

        if risk_warnings:
            risk_warning_message = (
                " Risk warning: "
                + "; ".join(risk_warnings)
            )

        paper_order = PaperOrder(
            account_id=account.id,
            ticker=clean_ticker,
            side=clean_side,
            order_type=MARKET_ORDER_TYPE,
            quantity=clean_quantity,
            requested_price=clean_price,
            executed_price=None,
            order_value=None,
            status="PENDING",
            rejection_reason=None,
            submitted_at=utc_now(),
            executed_at=None,
        )

        session.add(paper_order)
        session.flush()

        try:
            if clean_side == "BUY":
                position, order_value, realized_profit_loss = (
                    execute_buy_order(
                        session=session,
                        account=account,
                        ticker=clean_ticker,
                        quantity=clean_quantity,
                        execution_price=clean_price,
                    )
                )
            else:
                position, order_value, realized_profit_loss = (
                    execute_sell_order(
                        session=session,
                        account=account,
                        ticker=clean_ticker,
                        quantity=clean_quantity,
                        execution_price=clean_price,
                    )
                )

        except ValueError as validation_exception:
            paper_order.status = REJECTED_STATUS
            paper_order.rejection_reason = str(validation_exception)
            paper_order.executed_price = None
            paper_order.order_value = None
            paper_order.executed_at = None

            session.commit()
            session.refresh(paper_order)
            session.refresh(account)

            return build_order_result(
                success=False,
                message=str(validation_exception),
                order=paper_order,
                account=account,
            )

        executed_at = utc_now()

        paper_order.executed_price = clean_price
        paper_order.order_value = order_value
        paper_order.status = FILLED_STATUS
        paper_order.executed_at = executed_at

        paper_trade = PaperTrade(
            account_id=account.id,
            order_id=paper_order.id,
            ticker=clean_ticker,
            side=clean_side,
            quantity=clean_quantity,
            execution_price=clean_price,
            gross_value=order_value,
            realized_profit_loss=realized_profit_loss,
            executed_at=executed_at,
        )

        session.add(paper_trade)
        session.commit()

        session.refresh(account)
        session.refresh(position)
        session.refresh(paper_order)
        session.refresh(paper_trade)

        snapshot_success, snapshot_message, snapshot = (
            save_automatic_equity_snapshot(
                account_id=account.id,
            )
        )

        snapshot_note = ""

        if snapshot_success and snapshot is not None:
            snapshot_note = (
                f" Equity snapshot #{snapshot.id} saved."
            )
        elif not snapshot_success:
            snapshot_note = (
                " Trade filled, but automatic equity snapshot "
                "failed: "
                + str(snapshot_message)
            )

        return build_order_result(
            success=True,
            message=(
                f"{clean_side} order filled: "
                f"{clean_quantity:g} share(s) of {clean_ticker} "
                f"at ${clean_price:,.2f}."
                + risk_warning_message
                + snapshot_note
            ),
            order=paper_order,
            trade=paper_trade,
            position=position,
            account=account,
        )

    except Exception as error:
        session.rollback()

        return build_order_result(
            success=False,
            message="Paper order failed: " + str(error),
        )

    finally:
        session.close()
