"""Validation and audit helpers for paper-trading positions."""

from core.numbers import safe_float
from core.ticker import clean_ticker_symbol

import re


from core.paper_trading_constants import FLOAT_TOLERANCE
MINIMUM_VALID_PRICE = 0.01

# Standard application-supported format:
# - 1 to 5 letters
# - optional class/share suffix such as BRK.B or BRK-B
TICKER_PATTERN = re.compile(
    r"^[A-Z]{1,5}(?:[.-][A-Z]{1,2})?$"
)


def validate_ticker_format(value):
    """
    Validate an application-supported ticker format.

    Returns:
        tuple:
            valid,
            normalized ticker,
            error message
    """

    ticker = clean_ticker_symbol(value)

    if not ticker:
        return False, ticker, "Ticker cannot be empty."

    if not TICKER_PATTERN.fullmatch(ticker):
        return (
            False,
            ticker,
            (
                "Ticker must contain 1 to 5 letters with an "
                "optional class suffix, such as BRK.B or BRK-B."
            ),
        )

    return True, ticker, None


def audit_position_record(
    ticker,
    quantity,
    average_cost,
    current_price=None,
):
    """Audit one paper-position record without modifying it."""

    clean_ticker = clean_ticker_symbol(ticker)
    clean_quantity = safe_float(quantity)
    clean_average_cost = safe_float(average_cost)

    if current_price is None:
        clean_current_price = None
    else:
        clean_current_price = safe_float(current_price)

    issues = []

    ticker_valid, _, ticker_error = validate_ticker_format(
        clean_ticker
    )

    if not ticker_valid:
        issues.append(
            {
                "code": "INVALID_TICKER",
                "severity": "ERROR",
                "message": ticker_error,
            }
        )

    if clean_quantity < -FLOAT_TOLERANCE:
        issues.append(
            {
                "code": "NEGATIVE_QUANTITY",
                "severity": "ERROR",
                "message": "Position quantity cannot be negative.",
            }
        )
    elif clean_quantity <= FLOAT_TOLERANCE:
        issues.append(
            {
                "code": "ZERO_QUANTITY",
                "severity": "INFO",
                "message": (
                    "Position has no open shares and may be a "
                    "closed historical position."
                ),
            }
        )

    if (
        clean_quantity > FLOAT_TOLERANCE
        and clean_average_cost <= FLOAT_TOLERANCE
    ):
        issues.append(
            {
                "code": "MISSING_AVERAGE_COST",
                "severity": "ERROR",
                "message": (
                    "Open position has no valid average cost."
                ),
            }
        )
    elif (
        clean_quantity > FLOAT_TOLERANCE
        and clean_average_cost <= MINIMUM_VALID_PRICE
    ):
        issues.append(
            {
                "code": "NEGLIGIBLE_AVERAGE_COST",
                "severity": "WARNING",
                "message": (
                    "Average cost is at or below $0.01 and "
                    "should be verified."
                ),
            }
        )

    if current_price is not None:
        if (
            clean_quantity > FLOAT_TOLERANCE
            and clean_current_price <= FLOAT_TOLERANCE
        ):
            issues.append(
                {
                    "code": "INVALID_CURRENT_PRICE",
                    "severity": "ERROR",
                    "message": (
                        "Open position has no valid current price."
                    ),
                }
            )
        elif (
            clean_quantity > FLOAT_TOLERANCE
            and clean_current_price <= MINIMUM_VALID_PRICE
        ):
            issues.append(
                {
                    "code": "NEGLIGIBLE_CURRENT_PRICE",
                    "severity": "WARNING",
                    "message": (
                        "Current price is at or below $0.01 "
                        "and should be verified."
                    ),
                }
            )

    estimated_market_value = 0.0

    if clean_current_price is not None:
        estimated_market_value = (
            clean_quantity * clean_current_price
        )
    elif clean_average_cost > 0:
        estimated_market_value = (
            clean_quantity * clean_average_cost
        )

    blocking_codes = {
        "INVALID_TICKER",
        "NEGATIVE_QUANTITY",
        "MISSING_AVERAGE_COST",
        "INVALID_CURRENT_PRICE",
    }

    usable_for_rebalance = not any(
        issue["code"] in blocking_codes
        for issue in issues
    )

    return {
        "ticker": clean_ticker,
        "quantity": clean_quantity,
        "average_cost": clean_average_cost,
        "current_price": clean_current_price,
        "estimated_market_value": round(
            estimated_market_value,
            2,
        ),
        "usable_for_rebalance": usable_for_rebalance,
        "issue_count": len(issues),
        "issues": issues,
    }


def audit_position_rows(position_rows):
    """Audit multiple position dictionaries."""

    results = []

    for row in position_rows or []:
        results.append(
            audit_position_record(
                ticker=(
                    row.get("ticker")
                    or row.get("Ticker")
                ),
                quantity=row.get(
                    "quantity",
                    row.get("Shares", 0.0),
                ),
                average_cost=row.get(
                    "average_cost",
                    row.get("Average Cost", 0.0),
                ),
                current_price=row.get(
                    "current_price",
                    row.get("Current Price"),
                ),
            )
        )

    return results
