"""Tests for the standalone valuation calculation foundation."""
import pytest

from valuation.engine import ValuationInputs, calculate_valuation


def test_valid_ratios_and_normalized_ticker():
    result = calculate_valuation(ValuationInputs(" aapl ", 100, 5, 500, 100))
    assert result.ticker == "AAPL"
    assert result.pe_ratio == pytest.approx(20)
    assert result.free_cash_flow_yield == pytest.approx(0.05)
    assert result.warnings == ()


def test_missing_inputs_return_unavailable_ratios():
    result = calculate_valuation(ValuationInputs("MSFT", 100))
    assert result.pe_ratio is None
    assert result.free_cash_flow_yield is None
    assert len(result.warnings) == 2


@pytest.mark.parametrize("eps", [0, -2])
def test_nonpositive_earnings_do_not_produce_pe(eps):
    result = calculate_valuation(ValuationInputs("ABC", 100, eps, 10, 10))
    assert result.pe_ratio is None
    assert result.free_cash_flow_yield == pytest.approx(0.01)
    assert any("zero or negative" in warning for warning in result.warnings)


def test_negative_free_cash_flow_has_negative_yield_and_warning():
    result = calculate_valuation(ValuationInputs("ABC", 100, 5, -50, 10))
    assert result.free_cash_flow_yield == pytest.approx(-0.05)
    assert any("negative" in warning for warning in result.warnings)


def test_zero_free_cash_flow_has_zero_yield():
    result = calculate_valuation(ValuationInputs("ABC", 100, 5, 0, 10))
    assert result.free_cash_flow_yield == 0


def test_missing_shares_do_not_block_pe():
    result = calculate_valuation(ValuationInputs("ABC", 100, 5, 50))
    assert result.pe_ratio == pytest.approx(20)
    assert result.free_cash_flow_yield is None


@pytest.mark.parametrize("price", [0, -1, None, float("nan"), float("inf"), "100", True])
def test_invalid_price_rejected(price):
    with pytest.raises(ValueError, match="price"):
        calculate_valuation(ValuationInputs("ABC", price))


@pytest.mark.parametrize("shares", [0, -1, float("nan"), float("inf"), "10", True])
def test_invalid_shares_rejected(shares):
    with pytest.raises(ValueError, match="shares_outstanding"):
        calculate_valuation(ValuationInputs("ABC", 100, 5, 50, shares))


@pytest.mark.parametrize("field,value", [
    ("earnings_per_share", float("nan")),
    ("earnings_per_share", float("-inf")),
    ("free_cash_flow", float("inf")),
    ("free_cash_flow", "100"),
])
def test_invalid_optional_financial_inputs_rejected(field, value):
    kwargs = {"ticker": "ABC", "price": 100, field: value}
    with pytest.raises(ValueError, match=field):
        calculate_valuation(ValuationInputs(**kwargs))


def test_empty_ticker_rejected():
    with pytest.raises(ValueError, match="ticker"):
        calculate_valuation(ValuationInputs(" ", 100))


def test_result_is_immutable():
    result = calculate_valuation(ValuationInputs("ABC", 100, 5))
    with pytest.raises(AttributeError):
        result.pe_ratio = 99


def test_overflowing_market_cap_rejected():
    with pytest.raises(ValueError, match="market capitalization"):
        calculate_valuation(ValuationInputs("ABC", 1e308, 5, 1, 1e308))
