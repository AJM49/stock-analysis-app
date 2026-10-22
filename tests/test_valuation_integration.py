"""Integration tests use deterministic cache rows and no provider requests."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from valuation import integration

NOW = datetime(2026, 10, 22, tzinfo=UTC)


def profile(**changes):
    fields = {
        "eps": 5.0,
        "shares_outstanding": 1_000_000.0,
        "source": "Alpha Vantage Company Overview",
        "fetched_at": NOW.replace(tzinfo=None) - timedelta(hours=1),
    }
    fields.update(changes)
    return SimpleNamespace(**fields)


def test_cached_eps_produces_pe_without_fcf(monkeypatch):
    monkeypatch.setattr(integration, "get_cached_company_profile", lambda ticker: profile())
    result = integration.calculate_cached_valuation(" aapl ", 100.0, now=NOW)
    assert result.ticker == "AAPL"
    assert result.valuation.pe_ratio == pytest.approx(20.0)
    assert result.valuation.free_cash_flow_yield is None
    assert any("free cash flow is missing" in w for w in result.warnings)
    assert result.profile_source == "Alpha Vantage Company Overview"


def test_missing_profile_is_explicit(monkeypatch):
    monkeypatch.setattr(integration, "get_cached_company_profile", lambda ticker: None)
    result = integration.calculate_cached_valuation("MSFT", 100, now=NOW)
    assert result.valuation is None
    assert "unavailable" in result.warnings[0]


def test_missing_eps_keeps_pe_unavailable(monkeypatch):
    monkeypatch.setattr(integration, "get_cached_company_profile", lambda ticker: profile(eps=None))
    result = integration.calculate_cached_valuation("AAPL", 100, now=NOW)
    assert result.valuation.pe_ratio is None
    assert any("earnings per share is missing" in w for w in result.warnings)


def test_stale_profile_not_used(monkeypatch):
    old = NOW.replace(tzinfo=None) - timedelta(days=8)
    monkeypatch.setattr(integration, "get_cached_company_profile", lambda ticker: profile(fetched_at=old))
    result = integration.calculate_cached_valuation("AAPL", 100, now=NOW)
    assert result.valuation is None
    assert "stale" in result.warnings[0]


def test_missing_timestamp_not_used(monkeypatch):
    monkeypatch.setattr(integration, "get_cached_company_profile", lambda ticker: profile(fetched_at=None))
    result = integration.calculate_cached_valuation("AAPL", 100, now=NOW)
    assert result.valuation is None
    assert "timestamp" in result.warnings[0]


def test_future_timestamp_not_used(monkeypatch):
    monkeypatch.setattr(integration, "get_cached_company_profile", lambda ticker: profile(fetched_at=NOW + timedelta(minutes=1)))
    result = integration.calculate_cached_valuation("AAPL", 100, now=NOW)
    assert result.valuation is None
    assert "future" in result.warnings[0]


@pytest.mark.parametrize("price", [0, -1, float("nan"), "100"])
def test_invalid_price_rejected_even_without_profile(monkeypatch, price):
    monkeypatch.setattr(integration, "get_cached_company_profile", lambda ticker: None)
    with pytest.raises(ValueError, match="price"):
        integration.calculate_cached_valuation("AAPL", price, now=NOW)


def test_invalid_shares_rejected_by_engine(monkeypatch):
    monkeypatch.setattr(integration, "get_cached_company_profile", lambda ticker: profile(shares_outstanding=0))
    with pytest.raises(ValueError, match="shares_outstanding"):
        integration.calculate_cached_valuation("AAPL", 100, now=NOW)


def test_nonpositive_max_age_rejected():
    with pytest.raises(ValueError, match="max_profile_age"):
        integration.calculate_cached_valuation("AAPL", 100, max_profile_age=timedelta(0), now=NOW)
