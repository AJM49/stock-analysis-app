from datetime import UTC
from datetime import date
from datetime import datetime

from core.time import get_age_days, parse_last_fetched, utc_now


def test_utc_now_returns_naive_utc_datetime():
    before = datetime.now(UTC).replace(tzinfo=None)
    result = utc_now()
    after = datetime.now(UTC).replace(tzinfo=None)

    assert isinstance(result, datetime)
    assert result.tzinfo is None
    assert before <= result <= after

def test_parse_last_fetched_returns_none_for_none():
    assert parse_last_fetched(None) is None


def test_parse_last_fetched_preserves_datetime():
    value = datetime(2026, 10, 5, 12, 30)

    assert parse_last_fetched(value) is value


def test_parse_last_fetched_converts_date_to_midnight():
    value = date(2026, 10, 5)

    assert parse_last_fetched(value) == datetime(2026, 10, 5)


def test_parse_last_fetched_parses_iso_datetime():
    assert parse_last_fetched("2026-10-05T12:30:00") == datetime(
        2026,
        10,
        5,
        12,
        30,
    )


def test_parse_last_fetched_returns_none_for_invalid_value():
    assert parse_last_fetched("not-a-date") is None


def test_get_age_days_returns_none_for_none():
    assert get_age_days(None) is None
