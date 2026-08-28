from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.health_check_service import run_production_health_check


FILES_TO_COMPILE = [
    "stock_app.py",
    "database.py",
    "market_data.py",
    "ui_components.py",
    "services/health_check_service.py",
    "services/market_data_service.py",
    "ui/diagnostics_page.py",
    "core/app_logging.py",
    "core/user_messages.py",
    "scripts/run_health_check.py",
    "scripts/cache_freshness_report.py",
    "scripts/verify_cache_seed.py",
    "scripts/cache_refresh_targets.py",
    "scripts/cache_refresh_plan.py",
    "scripts/seed_cache_targets.py",
]


def run_command(command: list[str]) -> tuple[bool, str]:
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    output = (result.stdout + result.stderr).strip()
    return result.returncode == 0, output


def compile_files() -> bool:
    all_ok = True

    print("Compile checks")
    print("--------------")

    for file_path in FILES_TO_COMPILE:
        ok, output = run_command([sys.executable, "-m", "py_compile", 
file_path])
        status = "OK" if ok else "FAILED"

        print(f"{status}: {file_path}")

        if output:
            print(output)

        all_ok = all_ok and ok

    return all_ok


def check_health() -> bool:
    print("")
    print("Production health")
    print("-----------------")

    health = run_production_health_check()

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

    return health.is_healthy


def main() -> int:
    compile_ok = compile_files()
    health_ok = check_health()

    print("")
    print("Deployment verification result")
    print("------------------------------")

    if compile_ok and health_ok:
        print("PASS: deployment is ready")
        return 0

    print("FAIL: resolve issues before deployment")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
