from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import os

import streamlit as st
from sqlalchemy import text

from app_metadata import APP_VERSION, SPRINT_LABEL
from database import engine
from database import get_market_data_cache_summary
from market_data import is_market_data_quota_limited


@dataclass(frozen=True)
class HealthCheckResult:
    app_version: str
    sprint_label: str
    database_configured: bool
    alpha_vantage_configured: bool
    database_connected: bool
    market_cache_rows: int
    latest_market_data_fetch: str
    provider_quota_locked: bool
    errors: list[str]

    @property
    def is_healthy(self) -> bool:
        return self.database_configured and self.database_connected


def _secret_or_env_exists(name: str) -> bool:
    if os.getenv(name):
        return True

    try:
        return bool(st.secrets.get(name))
    except Exception:
        return False


def _check_database_connection() -> tuple[bool, str | None]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, None
    except Exception as error:
        return False, str(error)


def _summarize_market_cache(summary: Any) -> tuple[int, str]:
    if not summary:
        return 0, "No cached fetch found"

    if isinstance(summary, dict):
        row_count = summary.get("total_rows") or summary.get("row_count") or summary.get("cache_count") or 0
        latest_fetch = (
            summary.get("latest_fetch")
            or summary.get("latest_fetched_at")
            or summary.get("last_fetch")
            or summary.get("last_fetched")
        )
        return int(row_count or 0), str(latest_fetch or "No cached fetch found")

    if isinstance(summary, list):
        total_rows = 0
        latest_fetch = None

        for item in summary:
            if not isinstance(item, dict):
                continue

            total_rows += int(item.get("row_count") or 0)
            item_fetch = item.get("last_fetched") or item.get("latest_fetch")

            if item_fetch and (latest_fetch is None or item_fetch > latest_fetch):
                latest_fetch = item_fetch

        return total_rows, str(latest_fetch or "No cached fetch found")

    return 0, "No cached fetch found"


def run_production_health_check() -> HealthCheckResult:
    errors: list[str] = []

    database_configured = _secret_or_env_exists("DATABASE_URL")
    alpha_vantage_configured = _secret_or_env_exists("ALPHA_VANTAGE_API_KEY")

    database_connected, database_error = _check_database_connection()
    if database_error:
        errors.append("Database connection check failed.")

    cache_rows = 0
    latest_fetch = "No cached fetch found"

    try:
        cache_summary = get_market_data_cache_summary()
        cache_rows, latest_fetch = _summarize_market_cache(cache_summary)
    except Exception:
        errors.append("Market cache summary check failed.")

    try:
        provider_quota_locked = is_market_data_quota_limited()
    except Exception:
        provider_quota_locked = False
        errors.append("Provider quota status check failed.")

    return HealthCheckResult(
        app_version=APP_VERSION,
        sprint_label=SPRINT_LABEL,
        database_configured=database_configured,
        alpha_vantage_configured=alpha_vantage_configured,
        database_connected=database_connected,
        market_cache_rows=cache_rows,
        latest_market_data_fetch=latest_fetch,
        provider_quota_locked=provider_quota_locked,
        errors=errors,
    )
