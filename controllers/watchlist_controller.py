from __future__ import annotations

from datetime import date
from datetime import datetime

import pandas as pd


def classify_watchlist_freshness(market_date):
    if market_date is None or pd.isna(market_date):
        return None, "Missing"

    if isinstance(market_date, str):
        try:
            market_date = datetime.fromisoformat(
                market_date
            ).date()
        except ValueError:
            return None, "Missing"

    if isinstance(market_date, datetime):
        market_date = market_date.date()

    try:
        age_days = (
            date.today() - market_date
        ).days
    except TypeError:
        return None, "Missing"

    if age_days <= 7:
        return age_days, "Fresh"

    return age_days, "Stale"


def build_watchlist_reliability_data(metric_rows):
    if not metric_rows:
        return pd.DataFrame()

    metrics_df = pd.DataFrame(metric_rows).copy()

    ages = []
    freshness_states = []

    for market_date in metrics_df[
        "Latest Market Date"
    ]:
        age_days, freshness = (
            classify_watchlist_freshness(
                market_date
            )
        )

        ages.append(age_days)
        freshness_states.append(freshness)

    metrics_df["Market Age Days"] = ages
    metrics_df["Data Freshness"] = (
        freshness_states
    )

    return metrics_df


def build_watchlist_data_health(metrics_df):
    health = {
        "total_tickers": 0,
        "fresh_count": 0,
        "stale_count": 0,
        "missing_count": 0,
        "available_count": 0,
        "coverage_pct": 0.0,
        "freshness_pct": 0.0,
        "quality_score": 0.0,
        "quality_status": "No Data",
    }

    if metrics_df is None or metrics_df.empty:
        return health

    total_tickers = len(metrics_df)

    freshness = (
        metrics_df["Data Freshness"]
        if "Data Freshness" in metrics_df.columns
        else pd.Series(
            ["Missing"] * total_tickers,
            index=metrics_df.index,
        )
    )

    fresh_count = int(
        (freshness == "Fresh").sum()
    )
    stale_count = int(
        (freshness == "Stale").sum()
    )
    missing_count = int(
        (freshness == "Missing").sum()
    )

    available_count = (
        fresh_count + stale_count
    )

    coverage_pct = (
        available_count
        / total_tickers
        * 100
    )

    freshness_pct = (
        fresh_count
        / total_tickers
        * 100
    )

    quality_score = (
        (fresh_count * 1.0)
        + (stale_count * 0.5)
    ) / total_tickers * 100

    if quality_score >= 90:
        quality_status = "Excellent"
    elif quality_score >= 75:
        quality_status = "Good"
    elif quality_score >= 60:
        quality_status = "Fair"
    else:
        quality_status = "Poor"

    return {
        "total_tickers": total_tickers,
        "fresh_count": fresh_count,
        "stale_count": stale_count,
        "missing_count": missing_count,
        "available_count": available_count,
        "coverage_pct": coverage_pct,
        "freshness_pct": freshness_pct,
        "quality_score": quality_score,
        "quality_status": quality_status,
    }


def build_watchlist_reliability(health):
    if not health:
        health = {}

    total_tickers = int(
        health.get(
            "total_tickers",
            0,
        )
    )

    quality_status = str(
        health.get(
            "quality_status",
            "No Data",
        )
    )

    quality_score = float(
        health.get(
            "quality_score",
            0.0,
        )
    )

    coverage_pct = float(
        health.get(
            "coverage_pct",
            0.0,
        )
    )

    freshness_pct = float(
        health.get(
            "freshness_pct",
            0.0,
        )
    )

    if total_tickers == 0 or quality_status == "No Data":
        status = "Unavailable"
        severity = "info"
        message = (
            "Watchlist reliability is unavailable because "
            "there are no saved tickers with market data."
        )

    elif quality_status in {
        "Excellent",
        "Good",
    }:
        status = "Reliable"
        severity = "success"
        message = (
            "Watchlist monitoring is supported by strong "
            "market-data coverage and freshness."
        )

    elif quality_status == "Fair":
        status = "Use With Caution"
        severity = "warning"
        message = (
            "Some watchlist prices are stale or missing. "
            "Refresh affected symbols before relying on "
            "watchlist signals."
        )

    else:
        status = "Insufficient Data"
        severity = "error"
        message = (
            "Watchlist market-data quality is too weak for "
            "reliable monitoring."
        )

    return {
        "status": status,
        "severity": severity,
        "quality_score": quality_score,
        "coverage_pct": coverage_pct,
        "freshness_pct": freshness_pct,
        "message": message,
    }
