from datetime import UTC
from datetime import datetime

from core.time import utc_now


def test_utc_now_returns_naive_utc_datetime():
    before = datetime.now(UTC).replace(tzinfo=None)
    result = utc_now()
    after = datetime.now(UTC).replace(tzinfo=None)

    assert isinstance(result, datetime)
    assert result.tzinfo is None
    assert before <= result <= after
