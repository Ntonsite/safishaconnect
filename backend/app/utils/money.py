"""Money arithmetic. Always ``Decimal``; TZS is settled in whole shillings."""

from decimal import ROUND_HALF_UP, Decimal

WHOLE = Decimal("1")


def tzs(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(WHOLE, rounding=ROUND_HALF_UP)


def percent_of(amount: Decimal, percent: Decimal) -> Decimal:
    return tzs(amount * percent / Decimal(100))
