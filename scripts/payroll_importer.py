"""Import payroll rows from CSV or JSON files (offline, local only)."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from payroll_parser import parse_amount, parse_bool, parse_iso_date

REQUIRED_FIELDS = ("date", "amount")
OPTIONAL_FIELDS = ("paid_in_full", "source")
SUPPORTED_SUFFIXES = (".csv", ".json")


def _clean_row(raw: Any, index: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"row {index} must be an object")
    row = {str(k).strip().lower(): v for k, v in raw.items() if k is not None}
    for field in REQUIRED_FIELDS:
        if field not in row or row[field] is None or str(row[field]).strip() == "":
            raise ValueError(f"row {index} is missing required field: {field}")
    result: dict[str, Any] = {
        "date": parse_iso_date(row["date"], f"row {index} date").isoformat(),
        "amount": parse_amount(row["amount"], f"row {index} amount"),
    }
    paid = row.get("paid_in_full")
    result["paid_in_full"] = True if paid is None or str(paid).strip() == "" else parse_bool(
        paid, f"row {index} paid_in_full")
    source = row.get("source")
    result["source"] = None if source is None or str(source).strip() == "" else str(source).strip()
    return result


def import_payroll(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported file type {suffix!r}; use .csv or .json")
    if not path.is_file():
        raise FileNotFoundError(f"Payroll file not found: {path}")
    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            names = {(n or "").strip().lower() for n in (reader.fieldnames or [])}
            missing = [f for f in REQUIRED_FIELDS if f not in names]
            if missing:
                raise ValueError(f"CSV is missing required column(s): {', '.join(missing)}")
            raw_rows = list(reader)
    else:
        with path.open(encoding="utf-8-sig") as handle:
            try:
                data = json.load(handle)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
        if isinstance(data, dict):
            data = data.get("rows", data.get("payroll"))
        if not isinstance(data, list):
            raise ValueError("JSON must be a list of rows or an object with a 'rows' list")
        raw_rows = data
    return [_clean_row(r, i) for i, r in enumerate(raw_rows, start=1)]
