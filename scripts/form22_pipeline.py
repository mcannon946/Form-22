"""End-to-end Form 22 preparation pipeline.

Consumes normalized daily payroll rows, limits them to the DOI-based 52-week
window, determines dates paid in full, totals earnings by calendar month, and
prepares exact PDF field values. Does not calculate AWW or compensation rate.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Iterable

from payroll_parser import rows_for_form22
from form22_earnings_fields import build_earnings_field_values


def prepare_form22_payload(rows: Iterable[dict[str, Any]], date_of_injury: str) -> dict[str, Any]:
    selected = rows_for_form22(rows, date_of_injury)
    monthly: dict[int, Decimal] = defaultdict(lambda: Decimal('0'))
    paid_dates: list[str] = []

    for row in selected:
        d = date.fromisoformat(row['date'])
        monthly[d.month] += row['amount']
        if row['paid_in_full']:
            paid_dates.append(row['date'])

    values = {'Date of Injury': date.fromisoformat(date_of_injury).strftime('%m/%d/%Y')}
    values.update(build_earnings_field_values(dict(monthly)))
    return {
        'values': values,
        'paid_in_full_dates': sorted(set(paid_dates)),
        'included_rows': selected,
    }
