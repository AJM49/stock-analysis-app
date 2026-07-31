"""Paper-trading equity history, drawdown, and account reset service."""

from datetime import datetime
from math import isfinite

from database import PaperAccount
from database import PaperEquitySnapshot
from database import PaperOrder
from database import PaperPosition
from database import PaperTrade
from database import get_database_session


DEFAULT_STARTING_CASH = 100000.0
MONEY_PRECISION = 2
PERCENT_PRECISION = 4


def validate_starting_cash(starting_cash):
    """Validate and normalize a paper-account starting balance."""

    try:
        clean_value = float(starting_cash)
    except (TypeError, ValueError):
        return False, None, "Starting cash must be numeric."

    if not isfinite(clean_value):
        return False, None, "Starting cash must be finite."

    if clean_value <= 0:
        return False, None, "Starting cash must be greater than zero."

    return True, round(clean_value, MONEY_PRECISION), None


def get_latest_equity_snapshot(account_id):
    """Return the latest equity snapshot for a paper account."""

    session = get_database_session()

    try:
        return (
            session.query(PaperEquitySnapshot)
            .filter(
                PaperEquitySnapshot.account_id == int(account_id)
            )
            .order_by(
                PaperEquitySnapshot.snapshot_time.desc(),
                PaperEquitySnapshot.id.desc(),
            )
            .first()
        )

    finally:
        session.close()


def get_paper_equity_snapshots(account_id, limit=500):
    """Return paper-account equity history chronologically."""

    session = get_database_session()

    try:
        snapshots = (
            session.query(PaperEquitySnapshot)
            .filter(
                PaperEquitySnapshot.account_id == int(account_id)
            )
            .order_by(
                PaperEquitySnapshot.snapshot_time.desc(),
                PaperEquitySnapshot.id.desc(),
            )
            .limit(int(limit))
            .all()
        )

        return list(reversed(snapshots))

    finally:
        session.close()


def calculate_peak_equity(account_id, account_equity):
    """Return the highest recorded equity for an account."""

    session = get_database_session()

    try:
        latest_peak = (
            session.query(PaperEquitySnapshot.peak_equity)
            .filter(
                PaperEquitySnapshot.account_id == int(account_id)
            )
            .order_by(
                PaperEquitySnapshot.snapshot_time.desc(),
                PaperEquitySnapshot.id.desc(),
            )
            .first()
        )

        previous_peak = (
            float(latest_peak[0])
            if latest_peak and latest_peak[0] is not None
            else 0.0
        )

        return max(
            previous_peak,
            float(account_equity),
        )

    finally:
        session.close()


def save_equity_snapshot(
    account_id,
    cash_balance,
    market_value,
    starting_cash,
):
    """Save a paper-account equity and drawdown snapshot."""

    clean_cash = round(float(cash_balance), MONEY_PRECISION)
    clean_market_value = round(float(market_value), MONEY_PRECISION)
    clean_starting_cash = round(float(starting_cash), MONEY_PRECISION)

    account_equity = round(
        clean_cash + clean_market_value,
        MONEY_PRECISION,
    )

    total_profit_loss = round(
        account_equity - clean_starting_cash,
        MONEY_PRECISION,
    )

    if clean_starting_cash <= 0:
        total_return_pct = 0.0
    else:
        total_return_pct = round(
            total_profit_loss / clean_starting_cash * 100,
            PERCENT_PRECISION,
        )

    peak_equity = round(
        calculate_peak_equity(
            account_id=account_id,
            account_equity=account_equity,
        ),
        MONEY_PRECISION,
    )

    drawdown_value = round(
        account_equity - peak_equity,
        MONEY_PRECISION,
    )

    if peak_equity <= 0:
        drawdown_pct = 0.0
    else:
        drawdown_pct = round(
            drawdown_value / peak_equity * 100,
            PERCENT_PRECISION,
        )

    session = get_database_session()

    try:
        snapshot = PaperEquitySnapshot(
            account_id=int(account_id),
            snapshot_time=datetime.utcnow(),
            cash_balance=clean_cash,
            market_value=clean_market_value,
            account_equity=account_equity,
            total_profit_loss=total_profit_loss,
            total_return_pct=total_return_pct,
            peak_equity=peak_equity,
            drawdown_value=drawdown_value,
            drawdown_pct=drawdown_pct,
            created_at=datetime.utcnow(),
        )

        session.add(snapshot)
        session.commit()
        session.refresh(snapshot)

        return True, "Paper-equity snapshot saved.", snapshot

    except Exception as error:
        session.rollback()
        return False, "Snapshot error: " + str(error), None

    finally:
        session.close()



def calculate_transaction_market_value(account_id):
    """
    Calculate open-position value using each position's average cost.

    This creates a transaction-ledger valuation that does not depend
    on an external market-data request.
    """

    session = get_database_session()

    try:
        positions = (
            session.query(PaperPosition)
            .filter(
                PaperPosition.account_id == int(account_id),
                PaperPosition.quantity > 0,
            )
            .all()
        )

        market_value = 0.0

        for position in positions:
            market_value += (
                float(position.quantity)
                * float(position.average_cost)
            )

        return round(market_value, MONEY_PRECISION)

    finally:
        session.close()


def save_automatic_equity_snapshot(account_id):
    """
    Save an equity snapshot after a successfully filled trade.

    Snapshot valuation uses open-position cost basis so the trade
    transaction remains independent of market-data availability.
    """

    session = get_database_session()

    try:
        account = (
            session.query(PaperAccount)
            .filter(
                PaperAccount.id == int(account_id),
                PaperAccount.is_active.is_(True),
            )
            .first()
        )

        if account is None:
            return (
                False,
                "Automatic snapshot skipped: account not found.",
                None,
            )

        cash_balance = float(account.cash_balance)
        starting_cash = float(account.starting_cash)

    finally:
        session.close()

    market_value = calculate_transaction_market_value(
        account_id=account_id
    )

    return save_equity_snapshot(
        account_id=account_id,
        cash_balance=cash_balance,
        market_value=market_value,
        starting_cash=starting_cash,
    )


def reset_paper_account(
    account_id,
    starting_cash=DEFAULT_STARTING_CASH,
):
    """Reset paper account positions, orders, trades, and history."""

    valid, clean_starting_cash, validation_error = (
        validate_starting_cash(starting_cash)
    )

    if not valid:
        return False, validation_error

    session = get_database_session()

    try:
        account = (
            session.query(PaperAccount)
            .filter(
                PaperAccount.id == int(account_id),
                PaperAccount.is_active.is_(True),
            )
            .first()
        )

        if account is None:
            return False, "Active paper account was not found."

        session.query(PaperTrade).filter(
            PaperTrade.account_id == account.id
        ).delete(synchronize_session=False)

        session.query(PaperOrder).filter(
            PaperOrder.account_id == account.id
        ).delete(synchronize_session=False)

        session.query(PaperPosition).filter(
            PaperPosition.account_id == account.id
        ).delete(synchronize_session=False)

        session.query(PaperEquitySnapshot).filter(
            PaperEquitySnapshot.account_id == account.id
        ).delete(synchronize_session=False)

        account.starting_cash = clean_starting_cash
        account.cash_balance = clean_starting_cash
        account.updated_at = datetime.utcnow()

        session.commit()

        return (
            True,
            f"Paper account reset to ${clean_starting_cash:,.2f}.",
        )

    except Exception as error:
        session.rollback()
        return False, "Account reset failed: " + str(error)

    finally:
        session.close()
