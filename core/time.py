from datetime import UTC
from datetime import date
from datetime import datetime


def parse_last_fetched(value: object) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())

    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def get_age_days(last_fetched: datetime | None) -> int | None:
    if last_fetched is None:
        return None

    return (datetime.now() - last_fetched).days


def utc_now():
    """Return naive UTC for timestamp-without-timezone storage."""
    return datetime.now(UTC).replace(tzinfo=None)
