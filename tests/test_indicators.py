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

def test_stock_view_uses_canonical_rsi_signal() -> None:
    import indicators
    from ui import stock_views

    assert stock_views.get_rsi_signal is indicators.get_rsi_signal


def test_stock_view_uses_canonical_macd_signal() -> None:
    import indicators
    from ui import stock_views

    assert stock_views.get_macd_signal is indicators.get_macd_signal


def test_stock_view_macd_signal_matches_renderer_contract() -> None:
    from ui.stock_views import get_macd_signal

    assert get_macd_signal(2.0, 1.0) == "Bullish momentum"
    assert get_macd_signal(1.0, 2.0) == "Bearish momentum"
    assert get_macd_signal(1.0, 1.0) == "Neutral momentum"
