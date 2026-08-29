from __future__ import annotations

from datetime import date
from datetime import datetime


def get_watchlist_market_data_age_days(metric_row):
    market_date = metric_row.get(
        "Latest Market Date"
    )

    if market_date is None:
        return None

    if isinstance(market_date, datetime):
        market_date = market_date.date()

    if isinstance(market_date, date):
        return (
            date.today() - market_date
        ).days

    try:
        parsed_date = datetime.fromisoformat(
            str(market_date)
        ).date()
    except (TypeError, ValueError):
        return None

    return (
        date.today() - parsed_date
    ).days


def classify_watchlist_research_priority(metric_row):
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


def build_watchlist_research_queue(metric_rows):
    research_rows = []

    for metric_row in metric_rows or []:
        row = dict(metric_row)

        classification = (
            classify_watchlist_research_priority(
                row
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
