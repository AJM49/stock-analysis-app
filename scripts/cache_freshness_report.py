from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from core.cache_policy import FRESH_CACHE_DAYS
from core.cache_policy import STALE_CACHE_DAYS

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import get_market_data_cache_summary


FRESH_DAYS = FRESH_CACHE_DAYS
STALE_DAYS = STALE_CACHE_DAYS

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


def get_freshness_status(age_days: int | None) -> str:
    if age_days is None:
        return "missing"

    if age_days <= FRESH_DAYS:
        return "fresh"

    if age_days <= STALE_DAYS:
        return "aging"

    return "stale"


def main() -> int:
    summary = get_market_data_cache_summary()

    print("Market Data Cache Freshness Report")
    print("==================================")

    if not summary:
        print("No cached market data found.")
        return 1

    total_rows = 0
    status_counts = {
        "fresh": 0,
        "aging": 0,
        "stale": 0,
        "missing": 0,
    }

    print("")
    print("Ticker | Rows | Age | Status")
    print("-" * 78)

    for item in summary:
        ticker = item.get("ticker", "")
        row_count = int(item.get("row_count") or 0)
        oldest_date = str(item.get("oldest_date") or "")
        newest_date = str(item.get("newest_date") or "")
        last_fetched_raw = item.get("last_fetched")

        last_fetched = parse_last_fetched(last_fetched_raw)
        age_days = get_age_days(last_fetched)
        status = get_freshness_status(age_days)

        total_rows += row_count
        status_counts[status] += 1

        last_fetched_display = str(last_fetched_raw or "None")
        age_display = str(age_days) if age_days is not None else "-"

        print(
            ticker
            + " | "
            + str(row_count)
            + " | "
            + oldest_date
            + " | "
            + newest_date
            + " | "
            + last_fetched_display
            + " | "
            + age_display
            + " | "
            + status
        )

    print("")
    print("Summary")
    print("-------")
    print("Tickers: " + str(len(summary)))
    print("Rows: " + str(total_rows))
    print("Fresh: " + str(status_counts["fresh"]))
    print("Aging: " + str(status_counts["aging"]))
    print("Stale: " + str(status_counts["stale"]))
    print("Missing: " + str(status_counts["missing"]))

    if status_counts["stale"] or status_counts["missing"]:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
