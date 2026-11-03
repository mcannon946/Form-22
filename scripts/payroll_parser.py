"""NC Form 22 payroll normalization helpers.

Establishes the date-of-injury anchored 52-week reporting window and
normalizes payroll rows. This module does not calculate AWW or compensation rate.
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

TRUE_VALUES = {"true", "t", "yes", "y", "1", "paid", "paid in full"}
FALSE_VALUES = {"false", "f", "no", "n", "0", "not paid", "not paid in full", "unpaid"}


def parse_iso_date(value: Any, label: str = "date") -> date:
    if not isinstance(value, str):
        raise ValueError(f"{label} must use YYYY-MM-DD format")
    value = value.strip()
    if len(value) != 10:
        raise ValueError(f"{label} must use YYYY-MM-DD format: {value!r}")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid YYYY-MM-DD date: {value!r}") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{label} must use YYYY-MM-DD format: {value!r}")
    return parsed


def parse_bool(value: Any, label: str = "paid_in_full") -> bool:
    """Strictly parse a boolean; never uses bool() on text."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in TRUE_VALUES:
            return True
        if text in FALSE_VALUES:
            return False
    raise ValueError(f"{label} has invalid value: {value!r}")


def parse_amount(value: Any, label: str = "amount") -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{label} must be numeric: {value!r}")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{label} must be finite: {value!r}")
    text = str(value).strip().replace("$", "").replace(",", "")
    try:
        amount = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label} must be numeric: {value!r}") from exc
    if not amount.is_finite():
        raise ValueError(f"{label} must be finite: {value!r}")
    if amount < 0:
        raise ValueError(f"{label} must not be negative: {value!r}")
    return amount


def form22_reporting_window(date_of_injury: str) -> dict[str, str]:
    """52 weeks (364 days) immediately before the DOI; the DOI is excluded."""
    injury = parse_iso_date(date_of_injury, "date_of_injury")
    return {
        "start": (injury - timedelta(days=364)).isoformat(),
        "end": (injury - timedelta(days=1)).isoformat(),
        "date_of_injury": injury.isoformat(),
    }


def normalize_payroll_rows(rows: Iterable[dict[str, Any]], date_of_injury: str) -> list[dict[str, Any]]:
    if isinstance(rows, (str, bytes, dict)):
        raise TypeError("rows must be an iterable of row objects")
    window = form22_reporting_window(date_of_injury)
    start = date.fromisoformat(window["start"])
    end = date.fromisoformat(window["end"])
    normalized = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise TypeError(f"row {index} must be an object")
        work_date = parse_iso_date(row.get("date"), f"row {index} date")
        if "amount" not in row:
            raise ValueError(f"row {index} is missing amount")
        amount = parse_amount(row["amount"], f"row {index} amount")
        raw_paid = row.get("paid_in_full")
        paid = True if raw_paid is None or raw_paid == "" else parse_bool(raw_paid, f"row {index} paid_in_full")
        normalized.append({
            "date": work_date.isoformat(),
            "amount": amount,
            "paid_in_full": paid,
            "in_reporting_window": start <= work_date <= end,
            "source": row.get("source"),
        })
    return normalized


def rows_for_form22(rows: Iterable[dict[str, Any]], date_of_injury: str) -> list[dict[str, Any]]:
    return [r for r in normalize_payroll_rows(rows, date_of_injury) if r["in_reporting_window"]]
