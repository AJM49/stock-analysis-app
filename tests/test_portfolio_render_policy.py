from controllers.portfolio_controller import (
    build_portfolio_render_policy,
)


def test_reliable_portfolio_shows_derived_analytics():
    policy = build_portfolio_render_policy(
        {"status": "Reliable"}
    )

    assert policy["show_derived_analytics"] is True
    assert policy["show_caution"] is False


def test_caution_portfolio_still_shows_analytics():
    policy = build_portfolio_render_policy(
        {"status": "Use With Caution"}
    )

    assert policy["show_derived_analytics"] is True
    assert policy["show_caution"] is True


def test_insufficient_data_suppresses_derived_analytics():
    policy = build_portfolio_render_policy(
        {"status": "Insufficient Data"}
    )

    assert policy["show_derived_analytics"] is False
    assert policy["show_caution"] is True


def test_unavailable_data_suppresses_derived_analytics():
    policy = build_portfolio_render_policy(
        {"status": "Unavailable"}
    )

    assert policy["show_derived_analytics"] is False
    assert policy["show_caution"] is True


def test_missing_reliability_preserves_existing_behavior():
    policy = build_portfolio_render_policy(None)

    assert policy["show_derived_analytics"] is True
    assert policy["show_caution"] is False
