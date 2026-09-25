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
