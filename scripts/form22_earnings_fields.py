"""Map monthly earnings to Form 22 (08/2026) AcroForm dollar/cents fields.

Months are calendar months (1-12). Earnings are only mapped; no AWW or
compensation rate is calculated here.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Mapping

# (dollars field, cents field) per calendar month, Jan-Dec.
MONTH_EARNINGS_FIELDS: dict[int, tuple[str, str]] = {
    1: ("Amount Earned31", "Amount Earned31_2"),
    2: ("Amount Earned29", "Amount Earned29_2"),
    3: ("Amount Earned31_3", "Amount Earned31_4"),
    4: ("Amount Earned30", "Amount Earned30_2"),
    5: ("Amount Earned31_5", "Amount Earned31_6"),
    6: ("Amount Earned30_3", "Amount Earned30_4"),
    7: ("Amount Earned31_7", "Amount Earned31_8"),
    8: ("Amount Earned31_9", "Amount Earned31_10"),
    9: ("Amount Earned30_5", "Amount Earned30_6"),
    10: ("Amount Earned31_11", "Amount Earned31_12"),
    11: ("Amount Earned30_7", "Amount Earned30_8"),
    12: ("Amount Earned31_13", "Amount Earned31_14"),
}
TOTAL_EARNINGS_FIELDS = ("Amount EarnedTotal", "Amount EarnedTotal_2")


def split_dollars_cents(amount: Decimal) -> tuple[str, str]:
    cents_total = int((Decimal(amount) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if cents_total < 0:
        raise ValueError("amount must not be negative")
    return str(cents_total // 100), f"{cents_total % 100:02d}"


def earnings_field_values(monthly_totals: Mapping[int, Decimal], total: Decimal | None = None) -> dict[str, str]:
    """Return {field name: value}; `total` defaults to the sum of the months."""
    values: dict[str, str] = {}
    running = Decimal(0)
    for month, amount in monthly_totals.items():
        if month not in MONTH_EARNINGS_FIELDS:
            raise ValueError(f"invalid month: {month!r}")
        dollars_field, cents_field = MONTH_EARNINGS_FIELDS[month]
        values[dollars_field], values[cents_field] = split_dollars_cents(amount)
        running += Decimal(amount)
    values[TOTAL_EARNINGS_FIELDS[0]], values[TOTAL_EARNINGS_FIELDS[1]] = split_dollars_cents(
        running if total is None else total)
    return values
