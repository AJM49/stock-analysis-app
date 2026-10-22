"""UI tests for cached valuation research without provider calls."""
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from valuation.engine import ValuationResult
from valuation.integration import CachedValuationResult
from ui import valuation_views


def _result(valuation=None, warnings=()):
    return CachedValuationResult(
        ticker="AAPL",
        valuation=valuation,
        profile_source="Alpha Vantage Company Overview",
        profile_fetched_at=datetime(2026, 10, 21, 12),
        warnings=warnings,
    )


def test_display_valid_pe_and_unavailable_fcf(monkeypatch):
    mock_st = MagicMock()
    mock_st.columns.return_value = (MagicMock(), MagicMock())
    monkeypatch.setattr(valuation_views, "st", mock_st)
    result = _result(
        ValuationResult("AAPL", 20.0, None, ()),
        ("FCF yield unavailable: free cash flow is missing.",),
    )
    valuation_views.render_valuation_result(result)
    mock_st.columns.return_value[0].metric.assert_called_once_with(
        "Calculated trailing P/E", "20.00x"
    )
    mock_st.columns.return_value[1].metric.assert_called_once_with(
        "Free cash flow yield", "N/A"
    )
    mock_st.warning.assert_called_once_with(
        "FCF yield unavailable: free cash flow is missing."
    )
    captions = " ".join(call.args[0] for call in mock_st.caption.call_args_list)
    assert "Alpha Vantage Company Overview" in captions
    assert "2026-10-21 12:00 UTC" in captions
    assert "Not a real-time quote" in captions


def test_missing_profile_displays_unavailable_values(monkeypatch):
    mock_st = MagicMock()
    mock_st.columns.return_value = (MagicMock(), MagicMock())
    monkeypatch.setattr(valuation_views, "st", mock_st)
    valuation_views.render_valuation_result(
        CachedValuationResult("AAPL", None, None, None, ("Company profile unavailable in cache.",))
    )
    assert mock_st.columns.return_value[0].metric.call_args.args[1] == "N/A"
    assert mock_st.columns.return_value[1].metric.call_args.args[1] == "N/A"
    mock_st.warning.assert_called_once_with("Company profile unavailable in cache.")


def test_render_calls_integration_with_supplied_price(monkeypatch):
    mock_st = MagicMock()
    mock_st.columns.return_value = (MagicMock(), MagicMock())
    monkeypatch.setattr(valuation_views, "st", mock_st)
    called = []
    monkeypatch.setattr(
        valuation_views, "calculate_cached_valuation",
        lambda ticker, price: called.append((ticker, price)) or _result(),
    )
    valuation_views.render_cached_valuation_research("AAPL", 201.5)
    assert called == [("AAPL", 201.5)]


@pytest.mark.parametrize("error", [ValueError("bad price"), RuntimeError("database failed")])
def test_lookup_errors_do_not_crash_dashboard(monkeypatch, error):
    mock_st = MagicMock()
    mock_st.columns.return_value = (MagicMock(), MagicMock())
    monkeypatch.setattr(valuation_views, "st", mock_st)
    def fail(*args):
        raise error
    monkeypatch.setattr(valuation_views, "calculate_cached_valuation", fail)
    valuation_views.render_cached_valuation_research("AAPL", 100)
    assert mock_st.warning.called
    assert "Valuation unavailable" in mock_st.warning.call_args.args[0]


def test_missing_price_displays_unavailable_metrics(monkeypatch):
    mock_st = MagicMock()
    mock_st.columns.return_value = (MagicMock(), MagicMock())
    monkeypatch.setattr(valuation_views, "st", mock_st)

    valuation_views.render_valuation_unavailable()

    left, right = mock_st.columns.return_value
    left.metric.assert_called_once_with(
        "Calculated trailing P/E", "N/A"
    )
    right.metric.assert_called_once_with(
        "Free cash flow yield", "N/A"
    )
    assert "valid market price" in mock_st.warning.call_args.args[0]


def test_missing_price_does_not_query_fundamentals(monkeypatch):
    mock_st = MagicMock()
    mock_st.columns.return_value = (MagicMock(), MagicMock())
    monkeypatch.setattr(valuation_views, "st", mock_st)

    lookup = MagicMock()
    monkeypatch.setattr(
        valuation_views, "calculate_cached_valuation", lookup
    )

    valuation_views.render_valuation_unavailable()

    lookup.assert_not_called()
