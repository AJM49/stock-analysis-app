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


def _extract_cache_summary_value(summary: Any, *keys: str, default: Any = None) -> Any:
    if isinstance(summary, dict):
        for key in keys:
            if key in summary:
                return summary.get(key)
    return default


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
        cache_rows = int(
            _extract_cache_summary_value(
                cache_summary,
                "total_rows",
                "row_count",
                "cache_count",
                default=0,
            ) or 0
        )
        latest_fetch_value = _extract_cache_summary_value(
            cache_summary,
            "latest_fetch",
            "latest_fetched_at",
            "last_fetch",
            default=None,
        )
        if latest_fetch_value:
            latest_fetch = str(latest_fetch_value)
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
