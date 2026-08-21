from __future__ import annotations

from datetime import date
from datetime import datetime

import pandas as pd


WATCHLIST_FRESH_DAYS = 7


def _coerce_market_date(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    try:
        parsed = pd.to_datetime(
            value,
            errors="coerce",
        )
    except (TypeError, ValueError):
        return None

    if pd.isna(parsed):
        return None

    return parsed.date()


def classify_watchlist_data_freshness(
    cache_status,
    latest_market_date,
    today=None,
):
    if str(cache_status) != "Cached":
        return {
            "age_days": None,
            "freshness": "Missing",
        }

    market_date = _coerce_market_date(
        latest_market_date
    )

    if market_date is None:
        return {
            "age_days": None,
            "freshness": "Missing",
        }

    reference_date = today or date.today()

    age_days = (
        reference_date - market_date
    ).days

    if age_days <= WATCHLIST_FRESH_DAYS:
        freshness = "Fresh"
    else:
        freshness = "Stale"

    return {
        "age_days": age_days,
        "freshness": freshness,
    }


def classify_daily_move_signal(
    daily_change_pct,
):
    if daily_change_pct is None:
        return "No Move Data"

    try:
        change = float(daily_change_pct)
    except (TypeError, ValueError):
        return "No Move Data"

    if pd.isna(change):
        return "No Move Data"

    if change >= 3.0:
        return "Sharp Move Up"

    if change >= 1.0:
        return "Move Up"

    if change <= -3.0:
        return "Sharp Move Down"

    if change <= -1.0:
        return "Move Down"

    return "Quiet"


def classify_research_priority(
    freshness,
    daily_change_pct,
):
    if freshness in {
        "Missing",
        "Stale",
    }:
        return "High"

    try:
        absolute_change = abs(
            float(daily_change_pct)
        )
    except (TypeError, ValueError):
        return "Medium"

    if pd.isna(absolute_change):
        return "Medium"

    if absolute_change >= 3.0:
        return "High"

    if absolute_change >= 1.0:
        return "Medium"

    return "Low"


def build_watchlist_research_signals(
    metric_rows,
    today=None,
):
    signal_rows = []

    for row in metric_rows or []:
        enriched = dict(row)

        freshness_result = (
            classify_watchlist_data_freshness(
                row.get("Cache Status"),
                row.get(
                    "Latest Market Date"
                ),
                today=today,
            )
        )

        freshness = freshness_result[
            "freshness"
        ]

        daily_change_pct = row.get(
            "Daily Change %"
        )

        enriched["Data Freshness"] = (
            freshness
        )

        enriched["Data Age Days"] = (
            freshness_result["age_days"]
        )

        enriched["Move Signal"] = (
            classify_daily_move_signal(
                daily_change_pct
            )
        )

        enriched["Research Priority"] = (
            classify_research_priority(
                freshness,
                daily_change_pct,
            )
        )

        signal_rows.append(enriched)

    return signal_rows
