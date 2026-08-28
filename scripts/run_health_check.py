from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.health_check_service import run_production_health_check


def main() -> int:
    health = run_production_health_check()

    print("Production Health Check")
    print("=======================")
    print(f"App version: {health.app_version}")
    print(f"Release: {health.release_label}")
    print(f"Database configured: {health.database_configured}")
    print(f"Alpha Vantage configured: {health.alpha_vantage_configured}")
    print(f"Database connected: {health.database_connected}")
    print(f"Market cache rows: {health.market_cache_rows}")
    print(f"Latest cached fetch: {health.latest_market_data_fetch}")
    print(f"Provider quota locked: {health.provider_quota_locked}")
    print(f"Healthy: {health.is_healthy}")

    if health.errors:
        print("")
        print("Errors:")
        for item in health.errors:
            print(f"- {item}")

    return 0 if health.is_healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
