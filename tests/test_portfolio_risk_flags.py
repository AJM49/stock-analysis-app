import pandas as pd

from services.portfolio_analytics_service import (
    build_portfolio_risk_flags,
)


def _build_portfolio(weights: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Ticker": [
                f"TICKER_{index}"
                for index in range(len(weights))
            ],
            "Allocation %": weights,
        }
    )


def _build_sector(exposures: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Sector": [
                f"Sector_{index}"
                for index in range(len(exposures))
            ],
            "Exposure %": exposures,
        }
    )


def _find_flag(flags, risk_name):
    return next(
        (
            flag
            for flag in flags
            if flag["Risk"] == risk_name
        ),
        None,
    )


def test_high_single_position_concentration_flag():
    flags = build_portfolio_risk_flags(
        _build_portfolio([50.0, 30.0, 20.0])
    )

    flag = _find_flag(
        flags,
        "Single-position concentration",
    )

    assert flag is not None
    assert flag["Level"] == "High"


def test_medium_single_position_concentration_flag():
    flags = build_portfolio_risk_flags(
        _build_portfolio([30.0, 25.0, 25.0, 20.0])
    )

    flag = _find_flag(
        flags,
        "Single-position concentration",
    )

    assert flag is not None
    assert flag["Level"] == "Medium"


def test_low_single_position_concentration_has_no_flag():
    flags = build_portfolio_risk_flags(
        _build_portfolio([20.0] * 5)
    )

    assert _find_flag(
        flags,
        "Single-position concentration",
    ) is None


def test_high_sector_concentration_flag():
    flags = build_portfolio_risk_flags(
        _build_portfolio([25.0] * 4),
        _build_sector([50.0, 30.0, 20.0]),
    )

    flag = _find_flag(
        flags,
        "Sector concentration",
    )

    assert flag is not None
    assert flag["Level"] == "High"


def test_medium_sector_concentration_flag():
    flags = build_portfolio_risk_flags(
        _build_portfolio([25.0] * 4),
        _build_sector([40.0, 30.0, 30.0]),
    )

    flag = _find_flag(
        flags,
        "Sector concentration",
    )

    assert flag is not None
    assert flag["Level"] == "Medium"


def test_low_sector_concentration_has_no_flag():
    flags = build_portfolio_risk_flags(
        _build_portfolio([25.0] * 4),
        _build_sector([30.0, 25.0, 25.0, 20.0]),
    )

    assert _find_flag(
        flags,
        "Sector concentration",
    ) is None
