import math

import pytest

from services.paper_trading_analytics import calculate_profit_factor


def test_calculate_profit_factor_returns_finite_ratio() -> None:
    assert calculate_profit_factor(200.0, 100.0) == pytest.approx(2.0)


def test_calculate_profit_factor_normalizes_negative_gross_loss() -> None:
    assert calculate_profit_factor(200.0, -100.0) == pytest.approx(2.0)


def test_calculate_profit_factor_rounds_finite_ratio() -> None:
    assert calculate_profit_factor(199.0, 101.0) == pytest.approx(1.97)


def test_calculate_profit_factor_returns_infinity_without_losses() -> None:
    assert math.isinf(calculate_profit_factor(100.0, 0.0))


def test_calculate_profit_factor_returns_none_without_profit_or_loss() -> None:
    assert calculate_profit_factor(0.0, 0.0) is None
