"""Portfolio allocation drift and rebalance recommendations."""

from math import floor
from math import isfinite


MONEY_PRECISION = 2
PERCENT_PRECISION = 2
SHARE_PRECISION = 6
FLOAT_TOLERANCE = 1e-9

DEFAULT_REBALANCE_SETTINGS = {
    "drift_warning_pct": 2.0,
    "drift_rebalance_pct": 5.0,
    "minimum_cash_reserve_pct": 10.0,
    "allow_fractional_shares": True,
}


def safe_float(value, default=0.0):
    """Convert a value to a finite float."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(default)

    if not isfinite(number):
        return float(default)

    return number


def clamp(value, minimum, maximum):
    """Clamp a numeric value to a fixed range."""

    return max(minimum, min(maximum, value))


def normalize_ticker(value):
    """Normalize a ticker symbol."""

    return str(value or "").strip().upper()


def normalize_rebalance_settings(settings=None):
    """Return validated rebalance settings."""

    normalized = dict(DEFAULT_REBALANCE_SETTINGS)

    if settings:
        for key in normalized:
            if key in settings:
                normalized[key] = settings[key]

    normalized["drift_warning_pct"] = max(
        safe_float(
            normalized["drift_warning_pct"],
            DEFAULT_REBALANCE_SETTINGS[
                "drift_warning_pct"
            ],
        ),
        0.0,
    )

    normalized["drift_rebalance_pct"] = max(
        safe_float(
            normalized["drift_rebalance_pct"],
            DEFAULT_REBALANCE_SETTINGS[
                "drift_rebalance_pct"
            ],
        ),
        normalized["drift_warning_pct"],
    )

    normalized["minimum_cash_reserve_pct"] = clamp(
        safe_float(
            normalized["minimum_cash_reserve_pct"],
            DEFAULT_REBALANCE_SETTINGS[
                "minimum_cash_reserve_pct"
            ],
        ),
        0.0,
        100.0,
    )

    normalized["allow_fractional_shares"] = bool(
        normalized["allow_fractional_shares"]
    )

    return normalized


def normalize_target_allocations(target_allocations):
    """
    Normalize target allocations into a ticker-to-percent mapping.

    Target weights must be nonnegative and may total no more than
    100%. Any unallocated percentage is treated as target cash.
    """

    normalized = {}

    for raw_ticker, raw_weight in (
        target_allocations or {}
    ).items():
        ticker = normalize_ticker(raw_ticker)

        if not ticker:
            continue

        weight = safe_float(raw_weight)

        if weight < 0:
            raise ValueError(
                f"Target weight for {ticker} cannot be negative."
            )

        normalized[ticker] = round(
            weight,
            PERCENT_PRECISION,
        )

    total_target_weight = round(
        sum(normalized.values()),
        PERCENT_PRECISION,
    )

    if total_target_weight > 100.0 + FLOAT_TOLERANCE:
        raise ValueError(
            "Target position allocations cannot exceed 100%. "
            f"Current total: {total_target_weight:.2f}%."
        )

    return normalized


def classify_drift(
    drift_pct,
    warning_threshold_pct,
    rebalance_threshold_pct,
):
    """Classify an allocation drift value."""

    drift = safe_float(drift_pct)
    absolute_drift = abs(drift)

    if absolute_drift >= rebalance_threshold_pct:
        return (
            "REBALANCE",
            "UNDERWEIGHT" if drift > 0 else "OVERWEIGHT",
        )

    if absolute_drift >= warning_threshold_pct:
        return (
            "WATCH",
            "UNDERWEIGHT" if drift > 0 else "OVERWEIGHT",
        )

    return "ON TARGET", "ON TARGET"


def round_share_adjustment(
    share_adjustment,
    allow_fractional_shares,
):
    """Round a suggested share adjustment."""

    shares = safe_float(share_adjustment)

    if allow_fractional_shares:
        return round(shares, SHARE_PRECISION)

    if shares > 0:
        return float(floor(shares))

    if shares < 0:
        return float(-floor(abs(shares)))

    return 0.0


def calculate_rebalance_plan(
    account_equity,
    cash_balance,
    position_rows,
    target_allocations,
    settings=None,
):
    """
    Calculate portfolio drift and cash-aware rebalance actions.

    Position rows should contain:
    - ticker
    - quantity
    - current_price
    - market_value

    Target allocations are percentages of total account equity.
    """

    config = normalize_rebalance_settings(settings)
    targets = normalize_target_allocations(
        target_allocations
    )

    clean_equity = round(
        max(safe_float(account_equity), 0.0),
        MONEY_PRECISION,
    )
    clean_cash = round(
        max(safe_float(cash_balance), 0.0),
        MONEY_PRECISION,
    )

    current_positions = {}

    for raw_row in position_rows or []:
        ticker = normalize_ticker(
            raw_row.get("ticker")
            or raw_row.get("Ticker")
        )

        if not ticker:
            continue

        quantity = safe_float(
            raw_row.get(
                "quantity",
                raw_row.get("Shares", 0.0),
            )
        )

        current_price = safe_float(
            raw_row.get(
                "current_price",
                raw_row.get("Current Price", 0.0),
            )
        )

        market_value = safe_float(
            raw_row.get(
                "market_value",
                raw_row.get(
                    "Market Value",
                    quantity * current_price,
                ),
            )
        )

        current_positions[ticker] = {
            "ticker": ticker,
            "quantity": round(
                max(quantity, 0.0),
                SHARE_PRECISION,
            ),
            "current_price": round(
                max(current_price, 0.0),
                MONEY_PRECISION,
            ),
            "market_value": round(
                max(market_value, 0.0),
                MONEY_PRECISION,
            ),
        }

    tickers = sorted(
        set(current_positions) | set(targets)
    )

    target_position_total_pct = round(
        sum(targets.values()),
        PERCENT_PRECISION,
    )
    target_cash_pct = round(
        100.0 - target_position_total_pct,
        PERCENT_PRECISION,
    )

    minimum_cash_value = round(
        clean_equity
        * config["minimum_cash_reserve_pct"]
        / 100.0,
        MONEY_PRECISION,
    )

    available_buying_cash = round(
        max(clean_cash - minimum_cash_value, 0.0),
        MONEY_PRECISION,
    )

    rows = []
    alerts = []

    total_absolute_drift_pct = 0.0
    raw_buy_value = 0.0
    raw_sell_value = 0.0

    for ticker in tickers:
        position = current_positions.get(
            ticker,
            {
                "ticker": ticker,
                "quantity": 0.0,
                "current_price": 0.0,
                "market_value": 0.0,
            },
        )

        target_weight_pct = targets.get(ticker, 0.0)

        if clean_equity <= FLOAT_TOLERANCE:
            current_weight_pct = 0.0
        else:
            current_weight_pct = (
                position["market_value"]
                / clean_equity
                * 100.0
            )

        drift_pct = (
            target_weight_pct - current_weight_pct
        )

        absolute_drift_pct = abs(drift_pct)
        total_absolute_drift_pct += absolute_drift_pct

        alert_level, allocation_status = classify_drift(
            drift_pct=drift_pct,
            warning_threshold_pct=(
                config["drift_warning_pct"]
            ),
            rebalance_threshold_pct=(
                config["drift_rebalance_pct"]
            ),
        )

        target_value = round(
            clean_equity
            * target_weight_pct
            / 100.0,
            MONEY_PRECISION,
        )

        raw_adjustment_value = round(
            target_value - position["market_value"],
            MONEY_PRECISION,
        )

        if raw_adjustment_value > 0:
            raw_buy_value += raw_adjustment_value
        elif raw_adjustment_value < 0:
            raw_sell_value += abs(raw_adjustment_value)

        current_price = position["current_price"]

        if current_price <= FLOAT_TOLERANCE:
            raw_share_adjustment = 0.0
            recommendation_note = (
                "No share recommendation because a valid "
                "current price is unavailable."
            )
        else:
            raw_share_adjustment = (
                raw_adjustment_value / current_price
            )
            recommendation_note = ""

        suggested_adjustment_value = (
            raw_adjustment_value
        )

        if raw_adjustment_value > available_buying_cash:
            suggested_adjustment_value = (
                available_buying_cash
            )
            recommendation_note = (
                "Buy recommendation capped by the configured "
                "minimum cash reserve."
            )

        if current_price <= FLOAT_TOLERANCE:
            suggested_share_adjustment = 0.0
        else:
            suggested_share_adjustment = (
                suggested_adjustment_value
                / current_price
            )

        suggested_share_adjustment = (
            round_share_adjustment(
                share_adjustment=(
                    suggested_share_adjustment
                ),
                allow_fractional_shares=(
                    config[
                        "allow_fractional_shares"
                    ]
                ),
            )
        )

        if alert_level == "ON TARGET":
            suggested_adjustment_value = 0.0
            suggested_share_adjustment = 0.0
            action = "HOLD"
        elif suggested_share_adjustment > 0:
            action = "BUY"
        elif suggested_share_adjustment < 0:
            action = "SELL"
        else:
            action = "HOLD"

        if alert_level == "REBALANCE":
            alerts.append(
                f"{ticker} is {allocation_status.lower()} "
                f"by {absolute_drift_pct:.2f} percentage "
                "points."
            )
        elif alert_level == "WATCH":
            alerts.append(
                f"{ticker} drift is "
                f"{absolute_drift_pct:.2f} percentage points "
                "and should be monitored."
            )

        rows.append(
            {
                "ticker": ticker,
                "current_quantity": (
                    position["quantity"]
                ),
                "current_price": current_price,
                "current_value": (
                    position["market_value"]
                ),
                "current_weight_pct": round(
                    current_weight_pct,
                    PERCENT_PRECISION,
                ),
                "target_weight_pct": round(
                    target_weight_pct,
                    PERCENT_PRECISION,
                ),
                "drift_pct": round(
                    drift_pct,
                    PERCENT_PRECISION,
                ),
                "absolute_drift_pct": round(
                    absolute_drift_pct,
                    PERCENT_PRECISION,
                ),
                "allocation_status": (
                    allocation_status
                ),
                "alert_level": alert_level,
                "target_value": target_value,
                "raw_adjustment_value": (
                    raw_adjustment_value
                ),
                "raw_share_adjustment": round(
                    raw_share_adjustment,
                    SHARE_PRECISION,
                ),
                "suggested_adjustment_value": round(
                    suggested_adjustment_value,
                    MONEY_PRECISION,
                ),
                "suggested_share_adjustment": (
                    suggested_share_adjustment
                ),
                "suggested_action": action,
                "recommendation_note": (
                    recommendation_note
                ),
            }
        )

    rows.sort(
        key=lambda row: (
            row["absolute_drift_pct"],
            row["ticker"],
        ),
        reverse=True,
    )

    if clean_equity <= FLOAT_TOLERANCE:
        current_cash_pct = 0.0
    else:
        current_cash_pct = (
            clean_cash / clean_equity * 100.0
        )

    cash_drift_pct = round(
        target_cash_pct - current_cash_pct,
        PERCENT_PRECISION,
    )

    rebalance_required = any(
        row["alert_level"] == "REBALANCE"
        for row in rows
    )

    watch_required = any(
        row["alert_level"] == "WATCH"
        for row in rows
    )

    if rebalance_required:
        overall_status = "REBALANCE REQUIRED"
    elif watch_required:
        overall_status = "WATCH"
    else:
        overall_status = "ON TARGET"

    return {
        "account_equity": clean_equity,
        "cash_balance": clean_cash,
        "current_cash_pct": round(
            current_cash_pct,
            PERCENT_PRECISION,
        ),
        "target_cash_pct": target_cash_pct,
        "cash_drift_pct": cash_drift_pct,
        "minimum_cash_reserve_pct": (
            config["minimum_cash_reserve_pct"]
        ),
        "minimum_cash_value": minimum_cash_value,
        "available_buying_cash": (
            available_buying_cash
        ),
        "target_position_total_pct": (
            target_position_total_pct
        ),
        "total_absolute_drift_pct": round(
            total_absolute_drift_pct,
            PERCENT_PRECISION,
        ),
        "raw_buy_value": round(
            raw_buy_value,
            MONEY_PRECISION,
        ),
        "raw_sell_value": round(
            raw_sell_value,
            MONEY_PRECISION,
        ),
        "overall_status": overall_status,
        "rebalance_required": rebalance_required,
        "alerts": alerts,
        "rows": rows,
        "settings": config,
    }
