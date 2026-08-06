from datetime import date
from datetime import timedelta

import pandas as pd

from ui.stock_views import get_market_data_freshness


def build_history(days_old):
    market_date = date.today() - timedelta(days=days_old)

    return pd.DataFrame(
        {
            "Date": [pd.Timestamp(market_date)],
            "Close": [100.0],
            "Volume": [1_000_000],
        }
    )


def test_recent_market_data_is_fresh():
    history = build_history(days_old=2)

    latest_date, age_days, status = (
        get_market_data_freshness(history)
    )

    assert latest_date == date.today() - timedelta(days=2)
    assert age_days == 2
    assert status == "Fresh"


def test_four_day_old_market_data_is_delayed():
    history = build_history(days_old=4)

    _, age_days, status = get_market_data_freshness(
        history
    )

    assert age_days == 4
    assert status == "Delayed"


def test_old_market_data_is_stale():
    history = build_history(days_old=10)

    _, age_days, status = get_market_data_freshness(
        history
    )

    assert age_days == 10
    assert status == "Stale"


def test_empty_history_is_unavailable():
    history = pd.DataFrame()

    latest_date, age_days, status = (
        get_market_data_freshness(history)
    )

    assert latest_date is None
    assert age_days is None
    assert status == "Unavailable"


def test_missing_date_column_is_unavailable():
    history = pd.DataFrame(
        {
            "Close": [100.0],
        }
    )

    latest_date, age_days, status = (
        get_market_data_freshness(history)
    )

    assert latest_date is None
    assert age_days is None
    assert status == "Unavailable"


def test_invalid_dates_are_unavailable():
    history = pd.DataFrame(
        {
            "Date": ["not-a-date"],
        }
    )

    latest_date, age_days, status = (
        get_market_data_freshness(history)
    )

    assert latest_date is None
    assert age_days is None
    assert status == "Unavailable"
