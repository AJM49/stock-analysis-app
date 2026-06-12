from __future__ import annotations


ALLOWED_TICKER_CHARACTERS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ.-")
MAX_TICKER_LENGTH = 10


def clean_ticker_symbol(ticker: object) -> str:
    if ticker is None:
        return ""

    return str(ticker).upper().strip()


def is_valid_ticker_format(ticker: object) -> tuple[bool, str]:
    clean_ticker = clean_ticker_symbol(ticker)

    if not clean_ticker:
        return False, "Ticker cannot be empty."

    if len(clean_ticker) > MAX_TICKER_LENGTH:
        return False, "Ticker is too long."

    for character in clean_ticker:
        if character not in ALLOWED_TICKER_CHARACTERS:
            return False, "Ticker contains invalid characters."

    return True, clean_ticker


def validate_ticker(ticker: object) -> tuple[bool, str]:
    """
    Local-only validation.

    This must not call Alpha Vantage.
    Validation only checks input format.
    Market-data availability is handled by the market-data service.
    """
    return is_valid_ticker_format(ticker)
