from datetime import date
from datetime import timedelta

from services.watchlist_health_service import (
    build_watchlist_data_health,
    build_watchlist_research_reliability,
)


def test_watchlist_health_counts_fresh_stale_missing():
    today = date(2026, 8, 21)

    rows = [
        {
            "Cache Status": "Cached",
            "Latest Market Date": today,
        },
        {
            "Cache Status": "Cached",
            "Latest Market Date": (
                today - timedelta(days=10)
            ),
        },
        {
            "Cache Status": "Unavailable",
            "Latest Market Date": None,
        },
    ]

    health = build_watchlist_data_health(
        rows,
        today=today,
    )

    assert health["total_count"] == 3
    assert health["fresh_count"] == 1
    assert health["stale_count"] == 1
    assert health["missing_count"] == 1
    assert health["available_count"] == 2


def test_watchlist_health_calculates_coverage_and_freshness():
    today = date(2026, 8, 21)

    rows = [
        {
            "Cache Status": "Cached",
            "Latest Market Date": today,
        },
        {
            "Cache Status": "Cached",
            "Latest Market Date": (
                today - timedelta(days=20)
            ),
        },
        {
            "Cache Status": "Unavailable",
            "Latest Market Date": None,
        },
        {
            "Cache Status": "Unavailable",
            "Latest Market Date": None,
        },
    ]

    health = build_watchlist_data_health(
        rows,
        today=today,
    )

    assert health["coverage_pct"] == 50.0
    assert health["freshness_pct"] == 25.0
    assert health["quality_score"] == 37.5
    assert health["quality_status"] == "Poor"


def test_watchlist_health_handles_empty_rows():
    health = build_watchlist_data_health([])

    assert health["total_count"] == 0
    assert health["quality_status"] == "No Data"
    assert health["coverage_pct"] == 0.0



def test_good_watchlist_health_is_reliable():
    reliability = build_watchlist_research_reliability(
        {
            "total_count": 10,
            "quality_status": "Good",
            "quality_score": 80.0,
            "coverage_pct": 100.0,
            "freshness_pct": 80.0,
        }
    )

    assert reliability["status"] == "Reliable"
    assert reliability["severity"] == "success"
    assert reliability["research_ready"] is True


def test_fair_watchlist_health_requires_caution():
    reliability = build_watchlist_research_reliability(
        {
            "total_count": 10,
            "quality_status": "Fair",
            "quality_score": 65.0,
            "coverage_pct": 80.0,
            "freshness_pct": 50.0,
        }
    )

    assert reliability["status"] == "Use With Caution"
    assert reliability["severity"] == "warning"
    assert reliability["research_ready"] is False


def test_poor_watchlist_health_is_insufficient():
    reliability = build_watchlist_research_reliability(
        {
            "total_count": 10,
            "quality_status": "Poor",
            "quality_score": 35.0,
            "coverage_pct": 50.0,
            "freshness_pct": 20.0,
        }
    )

    assert reliability["status"] == "Insufficient Data"
    assert reliability["severity"] == "error"
    assert reliability["research_ready"] is False


def test_empty_watchlist_health_is_unavailable():
    reliability = build_watchlist_research_reliability(
        {
            "total_count": 0,
            "quality_status": "No Data",
            "quality_score": 0.0,
            "coverage_pct": 0.0,
            "freshness_pct": 0.0,
        }
    )

    assert reliability["status"] == "Unavailable"
    assert reliability["severity"] == "info"
    assert reliability["research_ready"] is False



def test_watchlist_good_health_is_reliable():
    reliability = build_watchlist_research_reliability(
        {
            "total_count": 10,
            "quality_status": "Good",
            "quality_score": 82.0,
            "coverage_pct": 100.0,
            "freshness_pct": 80.0,
        }
    )

    assert reliability["status"] == "Reliable"
    assert reliability["severity"] == "success"
    assert reliability["research_ready"] is True


def test_watchlist_fair_health_requires_caution():
    reliability = build_watchlist_research_reliability(
        {
            "total_count": 10,
            "quality_status": "Fair",
            "quality_score": 65.0,
            "coverage_pct": 80.0,
            "freshness_pct": 50.0,
        }
    )

    assert reliability["status"] == "Use With Caution"
    assert reliability["severity"] == "warning"
    assert reliability["research_ready"] is False


def test_watchlist_poor_health_is_insufficient():
    reliability = build_watchlist_research_reliability(
        {
            "total_count": 10,
            "quality_status": "Poor",
            "quality_score": 40.0,
            "coverage_pct": 50.0,
            "freshness_pct": 30.0,
        }
    )

    assert reliability["status"] == "Insufficient Data"
    assert reliability["severity"] == "error"
    assert reliability["research_ready"] is False


def test_watchlist_empty_health_is_unavailable():
    reliability = build_watchlist_research_reliability(
        {
            "total_count": 0,
            "quality_status": "No Data",
            "quality_score": 0.0,
            "coverage_pct": 0.0,
            "freshness_pct": 0.0,
        }
    )

    assert reliability["status"] == "Unavailable"
    assert reliability["severity"] == "info"
    assert reliability["research_ready"] is False
