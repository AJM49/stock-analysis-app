from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.cache_policy import CACHE_REFRESH_TARGET_TICKERS
from database import get_market_data_cache_summary
from database import save_market_data_cache
from market_data import fetch_alpha_vantage_daily_data
from market_data import is_provider_quota_error
from market_data import set_market_data_quota_limited


def get_cached_tickers() -> set[str]:
    summary = get_market_data_cache_summary()

    return {
        item.get("ticker")
        for item in summary
        if isinstance(item, dict) and item.get("ticker")
    }


def main() -> int:
    cached_tickers = get_cached_tickers()
    missing_tickers = [
        ticker
        for ticker in CACHE_REFRESH_TARGET_TICKERS
        if ticker not in cached_tickers
    ]

    print("Seed Cache Targets")
    print("==================")
    print("")

    if not missing_tickers:
        print("All cache refresh targets are already seeded.")
        return 0

    print("Missing targets:")
    for ticker in missing_tickers:
        print("- " + ticker)

    print("")
    seeded_count = 0

    for ticker in missing_tickers:
        print("Seeding " + ticker + "...")

        history, error = fetch_alpha_vantage_daily_data(ticker)

        if error:
            print("FAILED: " + ticker + " | " + error)

            if is_provider_quota_error(error):
                set_market_data_quota_limited(True)
                print("Provider quota lock enabled.")
                return 1

            continue

        if history.empty:
            print("FAILED: " + ticker + " | No market data returned.")
            continue

        save_market_data_cache(ticker, history)
        seeded_count += 1
        print("SEEDED: " + ticker + " | rows=" + str(len(history)))

    print("")
    print("Seeded tickers: " + str(seeded_count))
    print("Remaining missing tickers should be checked with scripts/cache_refresh_targets.py")

    if seeded_count == len(missing_tickers):
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
