import math


def finite_number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def optional_int(value):
    """Accept numeric integral values, treating absent or non-finite values as unknown."""
    number = finite_number(value)
    return int(number) if number is not None and number.is_integer() else None
