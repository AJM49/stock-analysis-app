from controllers.portfolio_controller import (
    build_portfolio_snapshot_save_policy,
)


def test_reliable_portfolio_can_save_snapshot():
    policy = build_portfolio_snapshot_save_policy(
        {"status": "Reliable"}
    )

    assert policy["allowed"] is True
    assert policy["status"] == "Reliable"


def test_caution_portfolio_can_save_snapshot():
    policy = build_portfolio_snapshot_save_policy(
        {"status": "Use With Caution"}
    )

    assert policy["allowed"] is True
    assert policy["status"] == "Use With Caution"


def test_insufficient_portfolio_cannot_save_snapshot():
    policy = build_portfolio_snapshot_save_policy(
        {"status": "Insufficient Data"}
    )

    assert policy["allowed"] is False
    assert policy["status"] == "Insufficient Data"


def test_unavailable_portfolio_cannot_save_snapshot():
    policy = build_portfolio_snapshot_save_policy(
        {"status": "Unavailable"}
    )

    assert policy["allowed"] is False
    assert policy["status"] == "Unavailable"



def test_missing_reliability_cannot_save_snapshot():
    policy = build_portfolio_snapshot_save_policy(
        None
    )

    assert policy["allowed"] is False
    assert policy["status"] == "Unavailable"
