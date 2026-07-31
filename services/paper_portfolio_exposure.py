"""Portfolio exposure and concentration analytics."""

from math import isfinite


MONEY_PRECISION = 2
PERCENT_PRECISION = 2
FLOAT_TOLERANCE = 1e-9

DEFAULT_EXPOSURE_SETTINGS = {
    "max_position_value_pct": 20.0,
    "warning_position_value_pct": 15.0,
    "minimum_cash_reserve_pct": 10.0,
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


def normalize_exposure_settings(settings=None):
    """Return validated exposure settings."""

    normalized = dict(DEFAULT_EXPOSURE_SETTINGS)

    if settings:
        for key in normalized:
            if key in settings:
                normalized[key] = safe_float(
                    settings[key],
                    normalized[key],
                )

    normalized["max_position_value_pct"] = max(
        normalized["max_position_value_pct"],
        0.01,
    )

    normalized["warning_position_value_pct"] = clamp(
        normalized["warning_position_value_pct"],
        0.0,
        normalized["max_position_value_pct"],
    )

    normalized["minimum_cash_reserve_pct"] = clamp(
        normalized["minimum_cash_reserve_pct"],
        0.0,
        100.0,
    )

    return normalized


def calculate_diversification_score(position_weights):
    """
    Calculate a normalized diversification score from 0 to 100.

    A single-position portfolio scores 0. An equally weighted
    multi-position portfolio approaches 100.
    """

    clean_weights = [
        safe_float(weight)
        for weight in position_weights
        if safe_float(weight) > FLOAT_TOLERANCE
    ]

    position_count = len(clean_weights)

    if position_count <= 1:
        return 0.0

    weight_fractions = [
        weight / 100.0
        for weight in clean_weights
    ]

    concentration_index = sum(
        weight ** 2
        for weight in weight_fractions
    )

    minimum_concentration = 1.0 / position_count

    denominator = 1.0 - minimum_concentration

    if denominator <= FLOAT_TOLERANCE:
        return 0.0

    score = (
        1.0
        - (
            concentration_index
            - minimum_concentration
        )
        / denominator
    ) * 100.0

    return round(
        clamp(score, 0.0, 100.0),
        PERCENT_PRECISION,
    )


def classify_concentration(
    position_weight_pct,
    warning_threshold_pct,
    maximum_threshold_pct,
):
    """Classify position concentration severity."""

    weight = safe_float(position_weight_pct)

    if weight >= maximum_threshold_pct:
        return "BLOCK"

    if weight >= warning_threshold_pct:
        return "WARNING"

    return "NORMAL"


def build_empty_exposure(cash_balance=0.0):
    """Return exposure analytics for an account with no positions."""

    clean_cash = round(
        safe_float(cash_balance),
        MONEY_PRECISION,
    )

    return {
        "cash_balance": clean_cash,
        "invested_value": 0.0,
        "account_equity": clean_cash,
        "cash_allocation_pct": 100.0 if clean_cash > 0 else 0.0,
        "invested_allocation_pct": 0.0,
        "position_count": 0,
        "largest_position_ticker": None,
        "largest_position_value": 0.0,
        "largest_position_weight_pct": 0.0,
        "concentration_index": 0.0,
        "diversification_score": 0.0,
        "total_unrealized_profit_loss": 0.0,
        "max_position_limit_pct": 0.0,
        "largest_position_limit_utilization_pct": 0.0,
        "cash_reserve_limit_pct": 0.0,
        "cash_reserve_utilization_pct": 0.0,
        "warnings": [],
        "positions": [],
    }


def calculate_portfolio_exposure(
    cash_balance,
    position_rows,
    settings=None,
):
    """
    Calculate portfolio exposure from normalized position dictionaries.

    Each position row should contain:
    - ticker
    - quantity
    - average_cost
    - current_price
    - cost_basis
    - market_value
    - unrealized_profit_loss
    """

    risk_settings = normalize_exposure_settings(settings)

    clean_cash = round(
        safe_float(cash_balance),
        MONEY_PRECISION,
    )

    normalized_positions = []

    for raw_row in position_rows or []:
        ticker = str(
            raw_row.get("ticker")
            or raw_row.get("Ticker")
            or "UNKNOWN"
        ).strip().upper()

        quantity = safe_float(
            raw_row.get(
                "quantity",
                raw_row.get("Shares", 0.0),
            )
        )

        if quantity <= FLOAT_TOLERANCE:
            continue

        average_cost = safe_float(
            raw_row.get(
                "average_cost",
                raw_row.get("Average Cost", 0.0),
            )
        )

        current_price = safe_float(
            raw_row.get(
                "current_price",
                raw_row.get("Current Price", average_cost),
            ),
            average_cost,
        )

        cost_basis = safe_float(
            raw_row.get(
                "cost_basis",
                raw_row.get(
                    "Cost Basis",
                    quantity * average_cost,
                ),
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

        unrealized_profit_loss = safe_float(
            raw_row.get(
                "unrealized_profit_loss",
                raw_row.get(
                    "Unrealized P/L",
                    market_value - cost_basis,
                ),
            )
        )

        normalized_positions.append(
            {
                "ticker": ticker,
                "quantity": round(quantity, 6),
                "average_cost": round(
                    average_cost,
                    MONEY_PRECISION,
                ),
                "current_price": round(
                    current_price,
                    MONEY_PRECISION,
                ),
                "cost_basis": round(
                    cost_basis,
                    MONEY_PRECISION,
                ),
                "market_value": round(
                    market_value,
                    MONEY_PRECISION,
                ),
                "unrealized_profit_loss": round(
                    unrealized_profit_loss,
                    MONEY_PRECISION,
                ),
            }
        )

    if not normalized_positions:
        empty_result = build_empty_exposure(clean_cash)
        empty_result["max_position_limit_pct"] = (
            risk_settings["max_position_value_pct"]
        )
        empty_result["cash_reserve_limit_pct"] = (
            risk_settings["minimum_cash_reserve_pct"]
        )
        return empty_result

    invested_value = sum(
        row["market_value"]
        for row in normalized_positions
    )

    account_equity = clean_cash + invested_value

    if account_equity <= FLOAT_TOLERANCE:
        cash_allocation_pct = 0.0
        invested_allocation_pct = 0.0
    else:
        cash_allocation_pct = (
            clean_cash / account_equity * 100.0
        )
        invested_allocation_pct = (
            invested_value / account_equity * 100.0
        )

    total_unrealized_profit_loss = sum(
        row["unrealized_profit_loss"]
        for row in normalized_positions
    )

    absolute_unrealized_total = sum(
        abs(row["unrealized_profit_loss"])
        for row in normalized_positions
    )

    warnings = []

    for row in normalized_positions:
        if account_equity <= FLOAT_TOLERANCE:
            portfolio_weight_pct = 0.0
        else:
            portfolio_weight_pct = (
                row["market_value"]
                / account_equity
                * 100.0
            )

        if invested_value <= FLOAT_TOLERANCE:
            invested_weight_pct = 0.0
        else:
            invested_weight_pct = (
                row["market_value"]
                / invested_value
                * 100.0
            )

        if absolute_unrealized_total <= FLOAT_TOLERANCE:
            unrealized_risk_contribution_pct = 0.0
        else:
            unrealized_risk_contribution_pct = (
                abs(row["unrealized_profit_loss"])
                / absolute_unrealized_total
                * 100.0
            )

        concentration_status = classify_concentration(
            position_weight_pct=portfolio_weight_pct,
            warning_threshold_pct=(
                risk_settings[
                    "warning_position_value_pct"
                ]
            ),
            maximum_threshold_pct=(
                risk_settings[
                    "max_position_value_pct"
                ]
            ),
        )

        limit_utilization_pct = (
            portfolio_weight_pct
            / risk_settings["max_position_value_pct"]
            * 100.0
        )

        row.update(
            {
                "portfolio_weight_pct": round(
                    portfolio_weight_pct,
                    PERCENT_PRECISION,
                ),
                "invested_weight_pct": round(
                    invested_weight_pct,
                    PERCENT_PRECISION,
                ),
                "unrealized_risk_contribution_pct": round(
                    unrealized_risk_contribution_pct,
                    PERCENT_PRECISION,
                ),
                "position_limit_utilization_pct": round(
                    limit_utilization_pct,
                    PERCENT_PRECISION,
                ),
                "concentration_status": (
                    concentration_status
                ),
            }
        )

        if concentration_status == "BLOCK":
            warnings.append(
                f'{row["ticker"]} represents '
                f'{portfolio_weight_pct:.2f}% of account equity, '
                f'exceeding the '
                f'{risk_settings["max_position_value_pct"]:.2f}% '
                "position limit."
            )
        elif concentration_status == "WARNING":
            warnings.append(
                f'{row["ticker"]} represents '
                f'{portfolio_weight_pct:.2f}% of account equity '
                "and is approaching the position limit."
            )

    normalized_positions.sort(
        key=lambda row: (
            row["market_value"],
            row["ticker"],
        ),
        reverse=True,
    )

    largest_position = normalized_positions[0]

    position_weights = [
        row["invested_weight_pct"]
        for row in normalized_positions
    ]

    concentration_index = sum(
        (weight / 100.0) ** 2
        for weight in position_weights
    )

    minimum_cash_reserve_pct = risk_settings[
        "minimum_cash_reserve_pct"
    ]

    if minimum_cash_reserve_pct <= FLOAT_TOLERANCE:
        cash_reserve_utilization_pct = 0.0
    else:
        cash_reserve_utilization_pct = (
            cash_allocation_pct
            / minimum_cash_reserve_pct
            * 100.0
        )

    if (
        cash_allocation_pct + FLOAT_TOLERANCE
        < minimum_cash_reserve_pct
    ):
        warnings.append(
            f"Cash allocation is {cash_allocation_pct:.2f}%, "
            f"below the required reserve of "
            f"{minimum_cash_reserve_pct:.2f}%."
        )

    return {
        "cash_balance": round(
            clean_cash,
            MONEY_PRECISION,
        ),
        "invested_value": round(
            invested_value,
            MONEY_PRECISION,
        ),
        "account_equity": round(
            account_equity,
            MONEY_PRECISION,
        ),
        "cash_allocation_pct": round(
            cash_allocation_pct,
            PERCENT_PRECISION,
        ),
        "invested_allocation_pct": round(
            invested_allocation_pct,
            PERCENT_PRECISION,
        ),
        "position_count": len(normalized_positions),
        "largest_position_ticker": (
            largest_position["ticker"]
        ),
        "largest_position_value": (
            largest_position["market_value"]
        ),
        "largest_position_weight_pct": (
            largest_position["portfolio_weight_pct"]
        ),
        "concentration_index": round(
            concentration_index,
            4,
        ),
        "diversification_score": (
            calculate_diversification_score(
                position_weights
            )
        ),
        "total_unrealized_profit_loss": round(
            total_unrealized_profit_loss,
            MONEY_PRECISION,
        ),
        "max_position_limit_pct": (
            risk_settings["max_position_value_pct"]
        ),
        "largest_position_limit_utilization_pct": round(
            largest_position[
                "position_limit_utilization_pct"
            ],
            PERCENT_PRECISION,
        ),
        "cash_reserve_limit_pct": (
            minimum_cash_reserve_pct
        ),
        "cash_reserve_utilization_pct": round(
            cash_reserve_utilization_pct,
            PERCENT_PRECISION,
        ),
        "warnings": warnings,
        "positions": normalized_positions,
    }
