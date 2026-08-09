from ui.portfolio_views import (
    get_portfolio_analytics_render_mode,
    should_render_portfolio_summary_metrics,
)


def reliability(status):
    return {
        "status": status,
    }


def test_reliable_portfolio_renders_full_analytics():
    result = reliability("Reliable")

    assert (
        get_portfolio_analytics_render_mode(result)
        == "full"
    )
    assert (
        should_render_portfolio_summary_metrics(
            result
        )
        is True
    )


def test_caution_portfolio_still_renders_analytics():
    result = reliability("Use With Caution")

    assert (
        get_portfolio_analytics_render_mode(result)
        == "caution"
    )
    assert (
        should_render_portfolio_summary_metrics(
            result
        )
        is True
    )


def test_insufficient_portfolio_uses_holdings_only():
    result = reliability("Insufficient Data")

    assert (
        get_portfolio_analytics_render_mode(result)
        == "holdings_only"
    )
    assert (
        should_render_portfolio_summary_metrics(
            result
        )
        is False
    )


def test_unavailable_portfolio_uses_holdings_only():
    result = reliability("Unavailable")

    assert (
        get_portfolio_analytics_render_mode(result)
        == "holdings_only"
    )
    assert (
        should_render_portfolio_summary_metrics(
            result
        )
        is False
    )
