import math

from indicators import get_volatility_signal


def test_get_volatility_signal_classifies_daily_percent_volatility() -> None:
    assert get_volatility_signal(0.5) == "Low volatility"
    assert get_volatility_signal(1.49) == "Low volatility"

    assert get_volatility_signal(1.5) == "Moderate volatility"
    assert get_volatility_signal(2.99) == "Moderate volatility"

    assert get_volatility_signal(3.0) == "High volatility"
    assert get_volatility_signal(4.5) == "High volatility"


def test_get_volatility_signal_handles_missing_data() -> None:
    assert get_volatility_signal(math.nan) == "Not enough data"
