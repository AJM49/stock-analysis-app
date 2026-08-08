from datetime import date
from datetime import timedelta

from portfolio import classify_cached_price_freshness


def test_cached_price_is_fresh_within_seven_days():
    price_date = date.today() - timedelta(days=3)

    age_days, status = classify_cached_price_freshness(
        price_date
    )

    assert age_days == 3
    assert status == "Fresh"


def test_cached_price_is_stale_after_seven_days():
    price_date = date.today() - timedelta(days=8)

    age_days, status = classify_cached_price_freshness(
        price_date
    )

    assert age_days == 8
    assert status == "Stale"


def test_missing_cached_price_is_missing():
    age_days, status = classify_cached_price_freshness(
        None
    )

    assert age_days is None
    assert status == "Missing"
