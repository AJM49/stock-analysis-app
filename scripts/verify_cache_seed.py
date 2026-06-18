from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import get_market_data_cache_summary


REQUIRED_TICKERS = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMD",
    "MU",
]


def main() -> int:
    summary = get_market_data_cache_summary()
    summary_by_ticker = {
        item.get("ticker"): item
        for item in summary
        if isinstance(item, dict)
    }

    missing = []

    print("Cache Seed Verification")
    print("=======================")
    print("")

    for ticker in REQUIRED_TICKERS:
        item = summary_by_ticker.get(ticker)

        if not item:
            print(ticker + ": MISSING")
            missing.append(ticker)
            continue

        print(ticker + ": CACHED")
        print("  Rows: " + str(item.get("row_count", 0)))
        print("  Oldest date: " + str(item.get("oldest_date", "")))
        print("  Newest date: " + str(item.get("newest_date", "")))
        print("  Last fetched: " + str(item.get("last_fetched", "")))
        print("")

    if missing:
        print("Missing cached tickers:")
        for ticker in missing:
            print("- " + ticker)
        return 1

    print("All required tickers are cached.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

