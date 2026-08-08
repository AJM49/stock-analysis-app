import pandas as pd

from services.company_research_service import (
    build_company_research_snapshot,
)


def test_snapshot_calculates_52_week_position():
    info = {
        "week_52_low": 100.0,
        "week_52_high": 200.0,
    }

    history = pd.DataFrame(
        {
            "Close": [150.0] * 20,
        }
    )

    snapshot = build_company_research_snapshot(
        info,
        history,
        175.0,
        25.0,
    )

    assert snapshot["range_position_pct"] == 75.0


def test_snapshot_detects_positive_trend():
    history = pd.DataFrame(
        {
            "Close": list(range(100, 120)),
        }
    )

    snapshot = build_company_research_snapshot(
        {},
        history,
        119.0,
        25.0,
    )

    assert snapshot["trend_status"] == "Positive"
    assert (
        "Price is above its 20-session average."
        in snapshot["signals"]
    )


def test_snapshot_flags_high_beta():
    snapshot = build_company_research_snapshot(
        {"beta": 1.5},
        pd.DataFrame(),
        100.0,
        25.0,
    )

    assert (
        "Beta indicates above-market price sensitivity."
        in snapshot["signals"]
    )


def test_snapshot_handles_missing_profile_fields():
    snapshot = build_company_research_snapshot(
        {},
        pd.DataFrame(),
        None,
        None,
    )

    assert snapshot["range_position_pct"] is None
    assert snapshot["trend_status"] == "Unavailable"
    assert snapshot["signals"] == []
