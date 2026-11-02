"""NC Form 22 payroll normalization helpers.

Establishes the date-of-injury anchored 52-week reporting window and
normalizes payroll rows for later mapping to the official Form 22.
This module fills the form; it does not calculate AWW or compensation rate.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable


def _parse_iso_date(value: str, label: str = "date") -> date:
    if not isinstance(value, str):
        raise TypeError(f"{label} must use YYYY-MM-DD format")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid date in YYYY-MM-DD format") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{label} must use YYYY-MM-DD format")
    return parsed


def form22_reporting_window(date_of_injury: str) -> dict[str, str]:
    injury = _parse_iso_date(date_of_injury, "date_of_injury")
    return {
        "start": (injury - timedelta(days=364)).isoformat(),
        "end": (injury - timedelta(days=1)).isoformat(),
        "date_of_injury": injury.isoformat(),
    }


def normalize_payroll_rows(rows: Iterable[dict[str, Any]], date_of_injury: str) -> list[dict[str, Any]]:
    if isinstance(rows, (str, bytes, dict)):
        raise TypeError("rows must be an iterable of row objects")
    window = form22_reporting_window(date_of_injury)
    start = _parse_iso_date(window["start"])
    end = _parse_iso_date(window["end"])
    normalized = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise TypeError(f"row {index} must be an object")
        work_date = _parse_iso_date(row.get("date"), f"row {index} date")
        try:
            amount = Decimal(str(row.get("amount", 0)))
        except (InvalidOperation, ValueError) as exc:
            raise TypeError(f"row {index} amount must be numeric") from exc
        if not amount.is_finite():
            raise TypeError(f"row {index} amount must be finite")
        normalized.append({
            "date": work_date.isoformat(),
            "amount": amount,
            "paid_in_full": bool(row.get("paid_in_full", True)),
            "in_reporting_window": start <= work_date <= end,
            "source": row.get("source"),
        })
    return normalized


def rows_for_form22(rows: Iterable[dict[str, Any]], date_of_injury: str) -> list[dict[str, Any]]:
    return [row for row in normalize_payroll_rows(rows, date_of_injury) if row["in_reporting_window"]]
