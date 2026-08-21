from __future__ import annotations


def build_watchlist_data_health(metric_rows):
    rows = list(metric_rows or [])

    health = {
        "total_count": 0,
        "cached_count": 0,
        "unavailable_count": 0,
        "coverage_pct": 0.0,
        "quality_status": "No Data",
    }

    if not rows:
        return health

    total_count = len(rows)

    cached_count = sum(
        1
        for row in rows
        if row.get("Cache Status") == "Cached"
    )

    unavailable_count = (
        total_count - cached_count
    )

    coverage_pct = (
        cached_count
        / total_count
        * 100
    )

    if coverage_pct >= 90:
        quality_status = "Excellent"
    elif coverage_pct >= 75:
        quality_status = "Good"
    elif coverage_pct >= 60:
        quality_status = "Fair"
    else:
        quality_status = "Poor"

    return {
        "total_count": total_count,
        "cached_count": cached_count,
        "unavailable_count": unavailable_count,
        "coverage_pct": coverage_pct,
        "quality_status": quality_status,
    }
