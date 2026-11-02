"""Earnings-field mapping helpers for NC Form 22 08/2026.

Maps monthly dollar/cents values and the total into the exact AcroForm field
names used by the official template. This does not calculate AWW.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping
from pypdf import PdfReader

MONTH_FIELDS = {
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
TOTAL_FIELDS = ("Amount EarnedTotal", "Amount EarnedTotal_2")


def _money_parts(value) -> tuple[str, str]:
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if amount < 0:
        raise ValueError("earnings cannot be negative")
    dollars = int(amount)
    cents = int((amount - Decimal(dollars)) * 100)
    return str(dollars), f"{cents:02d}"


def build_earnings_field_values(monthly_earnings: Mapping[int, object], include_total: bool = True) -> dict[str, str]:
    result: dict[str, str] = {}
    total = Decimal("0")
    for month, value in monthly_earnings.items():
        if month not in MONTH_FIELDS:
            raise ValueError(f"month must be 1-12: {month}")
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        dollars, cents = _money_parts(amount)
        dollar_field, cents_field = MONTH_FIELDS[month]
        result[dollar_field] = dollars
        result[cents_field] = cents
        total += amount
    if include_total:
        dollars, cents = _money_parts(total)
        result[TOTAL_FIELDS[0]] = dollars
        result[TOTAL_FIELDS[1]] = cents
    return result


def verify_template_fields(template: str) -> None:
    fields = PdfReader(template).get_fields() or {}
    expected = [name for pair in MONTH_FIELDS.values() for name in pair] + list(TOTAL_FIELDS)
    missing = [name for name in expected if name not in fields]
    if missing:
        raise KeyError(f"Missing earnings fields: {', '.join(missing)}")
