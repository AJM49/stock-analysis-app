from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.cache_policy import CACHE_REFRESH_TARGET_TICKERS
from core.cache_policy import FRESH_CACHE_DAYS
from core.cache_policy import STALE_CACHE_DAYS
from database import get_market_data_cache_summary


def parse_last_fetched(value: object) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())

    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def get_age_days(last_fetched: datetime | None) -> int | None:
    if last_fetched is None:
        return None

    return (datetime.now() - last_fetched).days


def get_status(age_days: int | None) -> str:
    if age_days is None:
        return "missing"

    if age_days <= FRESH_CACHE_DAYS:
        return "fresh"

    if age_days <= STALE_CACHE_DAYS:
        return "aging"

    return "stale"


def get_action(status: str) -> str:
    if status == "missing":
        return "seed ticker"

    if status == "stale":
        return "refresh soon"

    if status == "aging":
        return "monitor"

    return "no action"


def main() -> int:
    summary = get_market_data_cache_summary()
    summary_by_ticker = {
        item.get("ticker"): item
        for item in summary
        if isinstance(item, dict)
    }

    rows = []

    for ticker in CACHE_REFRESH_TARGET_TICKERS:
        item = summary_by_ticker.get(ticker)

        if not item:
            rows.append(
                {
                    "ticker": ticker,
                    "rows": 0,
                    "last_fetched": None,
                    "age_days": None,
                    "status": "missing",
                    "action": "seed ticker",
                    "priority": 0,
                }
            )
            continue

        last_fetched = parse_last_fetched(item.get("last_fetched"))
        age_days = get_age_days(last_fetched)
        status = get_status(age_days)

        priority = {
            "missing": 0,
            "stale": 1,
            "aging": 2,
            "fresh": 3,
        }.get(status, 9)

        rows.append(
            {
                "ticker": ticker,
                "rows": int(item.get("row_count") or 0),
                "last_fetched": str(item.get("last_fetched") or "None"),
                "age_days": age_days,
                "status": status,
                "action": get_action(status),
                "priority": priority,
            }
        )

    rows.sort(key=lambda row: (row["priority"], row["ticker"]))

    print("Cache Refresh Plan")
    print("==================")
    print("")
    print("Ticker | Rows | Age days | Status | Action | Last fetched")
    print("-" * 86)

    for row in rows:
        age_display = "-" if row["age_days"] is None else str(row["age_days"])

        print(
            row["ticker"]
            + " | "
            + str(row["rows"])
            + " | "
            + age_display
            + " | "
            + row["status"]
            + " | "
            + row["action"]
            + " | "
            + str(row["last_fetched"])
        )

    needs_action = [
        row
        for row in rows
        if row["status"] in {"missing", "stale"}
    ]

    print("")
    print("Summary")
    print("-------")
    print("Targets: " + str(len(rows)))
    print("Needs action: " + str(len(needs_action)))

    if needs_action:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
