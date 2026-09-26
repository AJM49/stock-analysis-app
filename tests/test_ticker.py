import pytest

from core.ticker import clean_ticker_symbol, is_valid_ticker_format


@pytest.mark.parametrize(
    ("raw_ticker", "expected"),
    [
        ("AAPL", "AAPL"),
        (" aapl ", "AAPL"),
        ("brk.b", "BRK.B"),
        ("brk-b", "BRK-B"),
        ("", ""),
        ("   ", ""),
        (None, ""),
    ],
)
def test_clean_ticker_symbol(raw_ticker, expected) -> None:
    assert clean_ticker_symbol(raw_ticker) == expected


@pytest.mark.parametrize(
    ("raw_ticker", "expected_normalized"),
    [
        ("AAPL", "AAPL"),
        (" aapl ", "AAPL"),
        ("BRK.B", "BRK.B"),
        ("brk-b", "BRK-B"),
    ],
)
def test_is_valid_ticker_format_accepts_supported_symbols(
    raw_ticker,
    expected_normalized,
) -> None:
    valid, normalized = is_valid_ticker_format(raw_ticker)

    assert valid is True
    assert normalized == expected_normalized


@pytest.mark.parametrize(
    "raw_ticker",
    [
        None,
        "",
        "   ",
    ],
)
def test_is_valid_ticker_format_rejects_empty_symbols(raw_ticker) -> None:
    valid, error = is_valid_ticker_format(raw_ticker)

    assert valid is False
    assert error == "Ticker cannot be empty."


def test_is_valid_ticker_format_rejects_overlong_symbol() -> None:
    valid, error = is_valid_ticker_format("ABCDEFGHIJK")

    assert valid is False
    assert error == "Ticker is too long."


@pytest.mark.parametrize(
    "raw_ticker",
    [
        "AAPL$",
        "AA PL",
        "AAPL/",
    ],
)
def test_is_valid_ticker_format_rejects_invalid_characters(raw_ticker) -> None:
    valid, error = is_valid_ticker_format(raw_ticker)

    assert valid is False
    assert error == "Ticker contains invalid characters."
