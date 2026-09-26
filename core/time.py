from datetime import UTC
from datetime import datetime


def utc_now():
    """Return naive UTC for timestamp-without-timezone storage."""
    return datetime.now(UTC).replace(tzinfo=None)
