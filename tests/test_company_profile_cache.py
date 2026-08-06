from __future__ import annotations

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import database
from services import market_data_service


@pytest.fixture
def isolated_profile_database(monkeypatch, tmp_path):
    test_database_path = tmp_path / "company_profile_cache.db"

    test_engine = create_engine(
        f"sqlite:///{test_database_path}",
        connect_args={"check_same_thread": False},
    )

    test_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )

    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(
        database,
        "SessionLocal",
        test_session_local,
    )

    database.Base.metadata.create_all(bind=test_engine)

    yield test_engine

    database.Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture
def apple_profile():
    return {
        "ticker": "AAPL",
        "longName": "Apple Inc",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "longBusinessSummary": (
            "Apple designs and sells consumer "
            "technology products."
        ),
        "marketCap": 3_000_000_000_000.0,
        "fiftyTwoWeekHigh": 250.0,
        "fiftyTwoWeekLow": 165.0,
        "trailingPE": 31.25,
        "dividendYield": 0.0045,
        "beta": 1.2,
        "source": "Alpha Vantage Company Overview",
    }


def make_history():
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(
                ["2026-08-04", "2026-08-05"]
            ),
            "Open": [200.0, 202.0],
            "High": [205.0, 206.0],
            "Low": [198.0, 201.0],
            "Close": [203.0, 205.0],
            "Adjusted Close": [203.0, 205.0],
            "Volume": [1_000_000, 1_100_000],
        }
    )


def test_save_and_load_company_profile_cache(
    isolated_profile_database,
    apple_profile,
):
    saved, message = database.save_company_profile_cache(
        "AAPL",
        apple_profile,
    )

    assert saved is True
    assert message == "AAPL company profile cached."

    cached_row = database.get_cached_company_profile("AAPL")

    assert cached_row is not None
    assert cached_row.ticker == "AAPL"
    assert cached_row.company_name == "Apple Inc"
    assert cached_row.sector == "Technology"
    assert cached_row.industry == "Consumer Electronics"
    assert cached_row.market_cap == 3_000_000_000_000.0


def test_company_profile_row_converts_to_ui_dictionary(
    isolated_profile_database,
    apple_profile,
):
    database.save_company_profile_cache(
        "AAPL",
        apple_profile,
    )

    cached_row = database.get_cached_company_profile("AAPL")
    profile = database.company_profile_row_to_dict(
        cached_row
    )

    assert profile["ticker"] == "AAPL"
    assert profile["longName"] == "Apple Inc"
    assert profile["sector"] == "Technology"
    assert profile["industry"] == "Consumer Electronics"
    assert profile["fiftyTwoWeekHigh"] == 250.0
    assert profile["fiftyTwoWeekLow"] == 165.0
    assert profile["trailingPE"] == 31.25
    assert profile["dividendYield"] == 0.0045
    assert profile["beta"] == 1.2
    assert profile["profileFetchedAt"] is not None


def test_save_company_profile_updates_existing_ticker(
    isolated_profile_database,
    apple_profile,
):
    database.save_company_profile_cache(
        "AAPL",
        apple_profile,
    )

    updated_profile = dict(apple_profile)
    updated_profile["longName"] = "Apple Incorporated"
    updated_profile["marketCap"] = 3_100_000_000_000.0

    saved, _ = database.save_company_profile_cache(
        "AAPL",
        updated_profile,
    )

    assert saved is True

    session = database.get_database_session()

    try:
        rows = (
            session.query(database.CompanyProfileCache)
            .filter(
                database.CompanyProfileCache.ticker == "AAPL"
            )
            .all()
        )
    finally:
        session.close()

    assert len(rows) == 1
    assert rows[0].company_name == "Apple Incorporated"
    assert rows[0].market_cap == 3_100_000_000_000.0


def test_load_cached_company_profile_returns_ui_dictionary(
    isolated_profile_database,
    apple_profile,
):
    database.save_company_profile_cache(
        "AAPL",
        apple_profile,
    )

    profile = (
        market_data_service.load_cached_company_profile(
            "AAPL"
        )
    )

    assert profile["longName"] == "Apple Inc"
    assert profile["sector"] == "Technology"
    assert profile["marketCap"] == 3_000_000_000_000.0


def test_load_stock_data_uses_cache_in_cache_only_mode(
    monkeypatch,
    apple_profile,
):
    history = make_history()

    monkeypatch.setattr(
        market_data_service,
        "get_stock_data",
        lambda *args, **kwargs: (history, None),
    )

    monkeypatch.setattr(
        market_data_service,
        "load_cached_company_profile",
        lambda ticker: apple_profile,
    )

    def fail_if_provider_called(*args, **kwargs):
        raise AssertionError(
            "Provider should not be called "
            "in cache-only mode."
        )

    monkeypatch.setattr(
        market_data_service,
        "fetch_alpha_vantage_company_overview",
        fail_if_provider_called,
    )

    info, loaded_history, error = (
        market_data_service.load_stock_data(
            "AAPL",
            "1mo",
            cache_only=True,
        )
    )

    assert error is None
    assert info["longName"] == "Apple Inc"
    assert info["sector"] == "Technology"
    assert loaded_history.equals(history)


def test_provider_quota_error_preserves_cached_profile(
    monkeypatch,
    apple_profile,
):
    history = make_history()

    monkeypatch.setattr(
        market_data_service,
        "get_stock_data",
        lambda *args, **kwargs: (history, None),
    )

    monkeypatch.setattr(
        market_data_service,
        "load_cached_company_profile",
        lambda ticker: apple_profile,
    )

    monkeypatch.setattr(
        market_data_service,
        "fetch_alpha_vantage_company_overview",
        lambda ticker: (
            {},
            "Market data provider limit reached.",
        ),
    )

    info, loaded_history, error = (
        market_data_service.load_stock_data(
            "AAPL",
            "1mo",
            cache_only=False,
        )
    )

    assert error is None
    assert info["longName"] == "Apple Inc"
    assert info["sector"] == "Technology"
    assert info["fiftyTwoWeekHigh"] == 250.0
    assert loaded_history.equals(history)
