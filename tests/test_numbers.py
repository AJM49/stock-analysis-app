import pytest

from core.numbers import safe_float


@pytest.mark.parametrize(
    ("value", "default", "expected"),
    [
        ("12.5", 0, 12.5),
        (None, 7, 7.0),
        ("invalid", 3, 3.0),
        (float("nan"), 4, 4.0),
        (float("inf"), 5, 5.0),
        (float("-inf"), 6, 6.0),
    ],
)
def test_safe_float(value, default, expected):
    assert safe_float(value, default) == expected


def test_clamp_limits_value_to_inclusive_range():
    from core.numbers import clamp

    assert clamp(5.0, 0.0, 10.0) == 5.0
    assert clamp(-1.0, 0.0, 10.0) == 0.0
    assert clamp(11.0, 0.0, 10.0) == 10.0
    assert clamp(0.0, 0.0, 10.0) == 0.0
    assert clamp(10.0, 0.0, 10.0) == 10.0
