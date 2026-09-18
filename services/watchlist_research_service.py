from __future__ import annotations

from datetime import date
from datetime import datetime


def get_watchlist_market_data_age_days(
    metric_row,
    today=None,
):
    if today is None:
        today = date.today()

    market_date = metric_row.get(
        "Latest Market Date"
    )

    if market_date is None:
        return None

    if isinstance(market_date, datetime):
        market_date = market_date.date()

    if isinstance(market_date, date):
        return (
            today - market_date
        ).days

    try:
        parsed_date = datetime.fromisoformat(
            str(market_date)
        ).date()
    except (TypeError, ValueError):
        return None

    return (
        today - parsed_date
    ).days


def classify_watchlist_research_priority(
    metric_row,
    today=None,
):
    cache_status = str(
        metric_row.get(
            "Cache Status",
            "",
        )
    )

    if cache_status != "Cached":
        return {
            "research_status": "Needs Data",
            "priority": 4,
            "reason": "No cached market data is available.",
        }

    age_days = get_watchlist_market_data_age_days(
        metric_row,
        today=today,
    )

    if age_days is None:
        return {
            "research_status": "Needs Data",
            "priority": 4,
            "reason": (
                "Market data freshness could not "
                "be determined."
            ),
        }

    if age_days > 7:
        return {
            "research_status": "Needs Data",
            "priority": 4,
            "reason": (
                f"Cached market data is "
                f"{age_days} days old."
            ),
        }

    daily_change = metric_row.get(
        "Daily Change %"
    )

    try:
        daily_change = float(daily_change)
    except (TypeError, ValueError):
        return {
            "research_status": "Needs Data",
            "priority": 4,
            "reason": "Daily price movement is unavailable.",
        }

    absolute_change = abs(daily_change)

    if absolute_change >= 5.0:
        return {
            "research_status": "Review Now",
            "priority": 3,
            "reason": (
                f"Daily price movement is "
                f"{daily_change:+.2f}%."
            ),
        }

    if absolute_change >= 2.0:
        return {
            "research_status": "Monitor",
            "priority": 2,
            "reason": (
                f"Daily price movement is "
                f"{daily_change:+.2f}%."
            ),
        }

    return {
        "research_status": "Stable",
        "priority": 1,
        "reason": (
            f"Daily price movement is "
            f"{daily_change:+.2f}%."
        ),
    }


def build_watchlist_research_queue(
    metric_rows,
    today=None,
):
    research_rows = []

    for metric_row in metric_rows or []:
        row = dict(metric_row)

        classification = (
            classify_watchlist_research_priority(
                row,
                today=today,
            )
        )

        row["Research Status"] = (
            classification[
                "research_status"
            ]
        )

        row["Research Priority"] = (
            classification["priority"]
        )

        row["Research Reason"] = (
            classification["reason"]
        )

        research_rows.append(row)

    return sorted(
        research_rows,
        key=lambda row: (
            -int(
                row["Research Priority"]
            ),
            str(row.get("Ticker", "")),
        ),
    )
