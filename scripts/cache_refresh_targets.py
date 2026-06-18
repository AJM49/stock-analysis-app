from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.cache_policy import CACHE_REFRESH_TARGET_TICKERS
from database import get_market_data_cache_summary


def main() -> int:
    summary = get_market_data_cache_summary()
    cached_tickers = {
        item.get("ticker")
        for item in summary
        if isinstance(item, dict)
    }

    missing = []

    print("Cache Refresh Target Report")
    print("===========================")
    print("")

    for ticker in CACHE_REFRESH_TARGET_TICKERS:
        if ticker in cached_tickers:
            print(ticker + ": cached")
        else:
            print(ticker + ": missing")
            missing.append(ticker)

    print("")
    print("Summary")
    print("-------")
    print("Targets: " + str(len(CACHE_REFRESH_TARGET_TICKERS)))
    print("Cached: " + str(len(CACHE_REFRESH_TARGET_TICKERS) - 
len(missing)))
    print("Missing: " + str(len(missing)))

    if missing:
        print("")
        print("Missing refresh targets:")
        for ticker in missing:
            print("- " + ticker)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
