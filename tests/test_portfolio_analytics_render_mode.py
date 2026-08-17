from controllers.portfolio_controller import (
    get_portfolio_analytics_render_mode,
)


def test_reliable_portfolio_uses_full_mode():
    assert get_portfolio_analytics_render_mode(
        {"status": "Reliable"}
    ) == "full"


def test_caution_portfolio_uses_caution_mode():
    assert get_portfolio_analytics_render_mode(
        {"status": "Use With Caution"}
    ) == "caution"


def test_insufficient_portfolio_uses_limited_mode():
    assert get_portfolio_analytics_render_mode(
        {"status": "Insufficient Data"}
    ) == "limited"


def test_unavailable_portfolio_uses_unavailable_mode():
    assert get_portfolio_analytics_render_mode(
        {"status": "Unavailable"}
    ) == "unavailable"
