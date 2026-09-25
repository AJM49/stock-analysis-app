from math import isfinite


def safe_float(value, default=0.0):
    """Convert a value to a finite float."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(default)

    if not isfinite(number):
        return float(default)

    return number
