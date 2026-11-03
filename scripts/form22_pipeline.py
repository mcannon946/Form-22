"""Connect payroll rows, the DOI window, monthly totals and paid-in-full dates.

Produces the payload consumed by pdf_population_engine. No AWW or
compensation-rate calculation is performed.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Iterable, Mapping

from form22_day_grid import field_for_date
from form22_earnings_fields import earnings_field_values
from payroll_parser import form22_reporting_window, rows_for_form22

DATE_OF_INJURY_FIELD = "Date of Injury"


def monthly_totals(rows: Iterable[Mapping[str, Any]]) -> dict[int, Decimal]:
    totals: dict[int, Decimal] = {}
    for row in rows:
        month = date.fromisoformat(row["date"]).month
        totals[month] = totals.get(month, Decimal(0)) + row["amount"]
    return totals


def build_payload(rows: Iterable[Mapping[str, Any]], date_of_injury: str,
                  extra_text_fields: Mapping[str, str] | None = None) -> dict[str, Any]:
    window = form22_reporting_window(date_of_injury)
    in_window = rows_for_form22(rows, date_of_injury)
    totals = monthly_totals(in_window)
    text_fields = dict(extra_text_fields or {})
    text_fields[DATE_OF_INJURY_FIELD] = date.fromisoformat(date_of_injury).strftime("%m/%d/%Y")
    text_fields.update(earnings_field_values(totals))
    paid_dates = sorted({r["date"] for r in in_window if r["paid_in_full"]})
    checkboxes = [field_for_date(date.fromisoformat(d)) for d in paid_dates]
    return {
        "window": window,
        "text_fields": text_fields,
        "checkboxes": checkboxes,
        "paid_in_full_dates": paid_dates,
        "monthly_totals": {m: str(v) for m, v in sorted(totals.items())},
    }
