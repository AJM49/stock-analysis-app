from __future__ import annotations

from services.watchlist_signal_service import (
    classify_watchlist_data_freshness,
)


def build_watchlist_data_health(
    metric_rows,
    today=None,
):
    rows = list(metric_rows or [])

    health = {
        "total_count": 0,
        "fresh_count": 0,
        "stale_count": 0,
        "missing_count": 0,
        "available_count": 0,
        "coverage_pct": 0.0,
        "freshness_pct": 0.0,
        "quality_score": 0.0,
        "quality_status": "No Data",
    }

    if not rows:
        return health

    total_count = len(rows)

    fresh_count = 0
    stale_count = 0
    missing_count = 0

    for row in rows:
        freshness_result = (
            classify_watchlist_data_freshness(
                row.get("Cache Status"),
                row.get("Latest Market Date"),
                today=today,
            )
        )

        freshness = freshness_result[
            "freshness"
        ]

        if freshness == "Fresh":
            fresh_count += 1
        elif freshness == "Stale":
            stale_count += 1
        else:
            missing_count += 1

    available_count = (
        fresh_count + stale_count
    )

    coverage_pct = (
        available_count
        / total_count
        * 100
    )

    freshness_pct = (
        fresh_count
        / total_count
        * 100
    )

    quality_score = (
        (fresh_count * 1.0)
        + (stale_count * 0.5)
    ) / total_count * 100

    if quality_score >= 90:
        quality_status = "Excellent"
    elif quality_score >= 75:
        quality_status = "Good"
    elif quality_score >= 60:
        quality_status = "Fair"
    else:
        quality_status = "Poor"

    return {
        "total_count": total_count,
        "fresh_count": fresh_count,
        "stale_count": stale_count,
        "missing_count": missing_count,
        "available_count": available_count,
        "coverage_pct": coverage_pct,
        "freshness_pct": freshness_pct,
        "quality_score": quality_score,
        "quality_status": quality_status,
    }



def build_watchlist_research_reliability(health):
    health = health or {}

    total_count = int(
        health.get(
            "total_count",
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

    if total_count == 0 or quality_status == "No Data":
        return {
            "status": "Unavailable",
            "severity": "info",
            "research_ready": False,
            "quality_score": quality_score,
            "coverage_pct": coverage_pct,
            "freshness_pct": freshness_pct,
            "message": (
                "Watchlist research reliability is unavailable "
                "because there are no symbols with usable "
                "market-data health information."
            ),
        }

    if quality_status in {
        "Excellent",
        "Good",
    }:
        return {
            "status": "Reliable",
            "severity": "success",
            "research_ready": True,
            "quality_score": quality_score,
            "coverage_pct": coverage_pct,
            "freshness_pct": freshness_pct,
            "message": (
                "Watchlist research is supported by strong "
                "market-data coverage and freshness."
            ),
        }

    if quality_status == "Fair":
        return {
            "status": "Use With Caution",
            "severity": "warning",
            "research_ready": False,
            "quality_score": quality_score,
            "coverage_pct": coverage_pct,
            "freshness_pct": freshness_pct,
            "message": (
                "Some watchlist symbols have stale or missing "
                "market data. Refresh affected symbols before "
                "using the watchlist for research decisions."
            ),
        }

    return {
        "status": "Insufficient Data",
        "severity": "error",
        "research_ready": False,
        "quality_score": quality_score,
        "coverage_pct": coverage_pct,
        "freshness_pct": freshness_pct,
        "message": (
            "Watchlist market-data quality is too weak for "
            "reliable research conclusions."
        ),
    }
