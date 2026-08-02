import pytest

from services.paper_position_validation import (
    audit_position_record,
    normalize_ticker,
    safe_float,
    validate_ticker_format,
)


def issue_codes(result):
    return {
        issue["code"]
        for issue in result["issues"]
    }


@pytest.mark.parametrize(
    ("raw_ticker", "expected"),
    [
        ("aapl", "AAPL"),
        (" BRK.B ", "BRK.B"),
        ("brk-b", "BRK-B"),
        (None, ""),
    ],
)
def test_normalize_ticker(raw_ticker, expected):
    assert normalize_ticker(raw_ticker) == expected


@pytest.mark.parametrize(
    "ticker",
    [
        "AAPL",
        "V",
        "MSFT",
        "BRK.B",
        "BRK-B",
    ],
)
def test_valid_ticker_formats_are_accepted(ticker):
    valid, normalized, error = validate_ticker_format(
        ticker
    )

    assert valid is True
    assert normalized == ticker
    assert error is None


@pytest.mark.parametrize(
    "ticker",
    [
        "",
        "AAPLMSFT",
        "AAPL MSFT",
        "$AAPL",
        "BRK/B",
        "1234",
        "AAPL!",
    ],
)
def test_invalid_ticker_formats_are_rejected(ticker):
    valid, normalized, error = validate_ticker_format(
        ticker
    )

    assert valid is False
    assert normalized == normalize_ticker(ticker)
    assert error


def test_valid_position_is_rebalance_eligible():
    result = audit_position_record(
        ticker="AAPL",
        quantity=10,
        average_cost=150,
        current_price=175,
    )

    assert result["usable_for_rebalance"] is True
    assert result["issue_count"] == 0
    assert result["estimated_market_value"] == 1750.0


def test_negative_quantity_blocks_rebalancing():
    result = audit_position_record(
        ticker="AAPL",
        quantity=-1,
        average_cost=150,
        current_price=175,
    )

    assert result["usable_for_rebalance"] is False
    assert "NEGATIVE_QUANTITY" in issue_codes(result)


def test_missing_average_cost_blocks_open_position():
    result = audit_position_record(
        ticker="AAPL",
        quantity=10,
        average_cost=0,
        current_price=175,
    )

    assert result["usable_for_rebalance"] is False
    assert "MISSING_AVERAGE_COST" in issue_codes(
        result
    )


def test_negligible_average_cost_is_warning_only():
    result = audit_position_record(
        ticker="VIX",
        quantity=10,
        average_cost=0.01,
        current_price=20,
    )

    assert result["usable_for_rebalance"] is True
    assert (
        "NEGLIGIBLE_AVERAGE_COST"
        in issue_codes(result)
    )


def test_invalid_current_price_blocks_open_position():
    result = audit_position_record(
        ticker="AAPL",
        quantity=10,
        average_cost=150,
        current_price=0,
    )

    assert result["usable_for_rebalance"] is False
    assert "INVALID_CURRENT_PRICE" in issue_codes(
        result
    )


def test_zero_quantity_is_informational_only():
    result = audit_position_record(
        ticker="AAPL",
        quantity=0,
        average_cost=0,
        current_price=0,
    )

    assert result["usable_for_rebalance"] is True
    assert "ZERO_QUANTITY" in issue_codes(result)


@pytest.mark.parametrize(
    ("value", "default", "expected"),
    [
        ("12.5", 0, 12.5),
        (None, 7, 7.0),
        ("invalid", 3, 3.0),
        (float("nan"), 4, 4.0),
        (float("inf"), 5, 5.0),
    ],
)
def test_safe_float(value, default, expected):
    assert safe_float(value, default) == expected
