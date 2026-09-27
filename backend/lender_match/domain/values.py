"""Helpers for classifying and comparing values."""

from datetime import date
from decimal import Decimal
from typing import Any


def is_integer(value: Any) -> bool:
    # bool is a subclass of int, so rule it out explicitly.
    return isinstance(value, int) and not isinstance(value, bool)


def is_number(value: Any) -> bool:
    return is_integer(value) or isinstance(value, float | Decimal)


def is_probability(value: Any) -> bool:
    return is_number(value) and 0 <= value <= 1


def to_decimal(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


DAYS_PER_YEAR = Decimal("365.25")


def years_between(start: date, end: date) -> Decimal:
    days = Decimal((end - start).days)
    return (days / DAYS_PER_YEAR).quantize(Decimal("0.1"))
