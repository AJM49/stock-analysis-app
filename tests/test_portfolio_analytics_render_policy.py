from controllers.portfolio_controller import (
    build_portfolio_render_policy,
)


def test_reliable_analytics_render_fully():
    policy = build_portfolio_render_policy(
        {
            "status": "Reliable",
        }
    )

    assert policy["mode"] == "full"
    assert policy["show_derived_analytics"] is True


def test_caution_analytics_still_render():
    policy = build_portfolio_render_policy(
        {
            "status": "Use With Caution",
        }
    )

    assert policy["mode"] == "caution"
    assert policy["show_derived_analytics"] is True


def test_insufficient_data_suppresses_derived_analytics():
    policy = build_portfolio_render_policy(
        {
            "status": "Insufficient Data",
        }
    )

    assert policy["mode"] == "restricted"
    assert policy["show_derived_analytics"] is False


def test_unavailable_analytics_are_suppressed():
    policy = build_portfolio_render_policy(
        {
            "status": "Unavailable",
        }
    )

    assert policy["mode"] == "unavailable"
    assert policy["show_derived_analytics"] is False
