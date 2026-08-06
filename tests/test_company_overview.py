from services.market_data_service import (
    parse_alpha_vantage_company_overview,
)
from services.market_data_service import safe_optional_float


def test_safe_optional_float_converts_valid_number():
    assert safe_optional_float("123.45") == 123.45


def test_safe_optional_float_returns_none_for_missing_value():
    assert safe_optional_float("None") is None
    assert safe_optional_float("N/A") is None
    assert safe_optional_float("") is None
    assert safe_optional_float(None) is None


def test_parse_company_overview_maps_expected_fields():
    payload = {
        "Symbol": "AAPL",
        "Name": "Apple Inc",
        "Description": "Technology company.",
        "Sector": "Technology",
        "Industry": "Consumer Electronics",
        "MarketCapitalization": "3000000000000",
        "52WeekHigh": "250.00",
        "52WeekLow": "165.00",
        "PERatio": "31.25",
        "DividendYield": "0.0045",
        "Beta": "1.20",
    }

    profile, error = parse_alpha_vantage_company_overview(
        payload,
        "AAPL",
    )

    assert error is None
    assert profile["longName"] == "Apple Inc"
    assert profile["sector"] == "Technology"
    assert profile["industry"] == "Consumer Electronics"
    assert profile["fiftyTwoWeekHigh"] == 250.0
    assert profile["fiftyTwoWeekLow"] == 165.0
    assert profile["marketCap"] == 3000000000000.0
    assert profile["trailingPE"] == 31.25
    assert profile["dividendYield"] == 0.0045
    assert profile["beta"] == 1.2


def test_parse_company_overview_rejects_empty_payload():
    profile, error = parse_alpha_vantage_company_overview(
        {},
        "AAPL",
    )

    assert profile == {}
    assert error == "No company overview found for AAPL"
