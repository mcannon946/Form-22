"""Offline text extraction and conservative payroll-row candidates for PDF records."""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader

from payroll_parser import form22_reporting_window, parse_amount

DATE_RE = re.compile(r"\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})\b")
AMOUNT_RE = re.compile(r"(?<![\w/])\$?\s*\(?\d[\d,]*(?:\.\d{2})\)?(?![\w/])")
PAID_RE = re.compile(r"\bpaid\s+in\s+full\b", re.IGNORECASE)
UNPAID_RE = re.compile(r"\b(?:not\s+paid\s+in\s+full|unpaid)\b", re.IGNORECASE)
PERIOD_RE = re.compile(r"\bpay(?:roll)?\s+period\b", re.IGNORECASE)


def _parse_document_date(text: str) -> str | None:
    try:
        if re.match(r"^\d{4}", text):
            year, month, day = map(int, re.split(r"[-/]", text))
        else:
            month, day, year = map(int, re.split(r"[-/]", text))
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _line_amounts(line: str, date_matches: list[re.Match[str]]) -> list[Decimal]:
    remainder = line
    for match in reversed(date_matches):
        remainder = remainder[:match.start()] + (" " * (match.end() - match.start())) + remainder[match.end():]
    amounts = []
    for match in AMOUNT_RE.finditer(remainder):
        try:
            amounts.append(parse_amount(match.group().strip()))
        except ValueError:
            continue
    return amounts


def _candidate_from_line(line: str, filename: str, page: int) -> dict[str, Any] | None:
    dates = DATE_RE.findall(line)
    date_matches = list(DATE_RE.finditer(line))
    amounts = _line_amounts(line, date_matches)
    if not amounts:
        return None

    payroll_date = _parse_document_date(dates[0]) if len(dates) == 1 else None
    period = None
    if len(dates) >= 2 and PERIOD_RE.search(line):
        start, end = (_parse_document_date(value) for value in dates[:2])
        if start and end:
            period = {"start": start, "end": end}
    if not payroll_date and not period:
        return None

    paid: bool | None = None
    if UNPAID_RE.search(line):
        paid = False
    elif PAID_RE.search(line):
        paid = True
    source = f"{filename}, page {page}"
    return {
        "date": payroll_date or "",
        "amount": amounts[-1],
        "paid_in_full": paid,
        "source": source,
        "period": period,
        "provenance": {"filename": filename, "page": page, "snippet": line.strip()},
        "field_status": {
            "date": "Extracted" if payroll_date else "Missing",
            "amount": "Extracted",
            "paid_in_full": "Extracted" if paid is not None else "Missing",
        },
        "review_status": "Needs review",
        "include": True,
    }


def mark_row_relationships(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mark exact duplicates and same-date amount conflicts without dropping rows."""
    marked = [dict(row) for row in rows]
    for row in marked:
        row.pop("duplicate_of", None)
        row["duplicate"] = False
        row["conflict"] = False
    first_by_key: dict[tuple[str, Decimal], int] = {}
    amounts_by_date: dict[str, set[Decimal]] = {}
    for index, row in enumerate(marked):
        work_date = row.get("date")
        amount = row.get("amount")
        if not work_date or amount is None:
            continue
        amount_value = Decimal(str(amount))
        key = (str(work_date), amount_value)
        if key in first_by_key:
            row["duplicate_of"] = first_by_key[key]
            row["duplicate"] = True
            marked[first_by_key[key]]["duplicate"] = True
        else:
            first_by_key[key] = index
        amounts_by_date.setdefault(str(work_date), set()).add(amount_value)
    for row in marked:
        work_date = row.get("date")
        row["conflict"] = bool(work_date and len(amounts_by_date.get(str(work_date), ())) > 1)
    return marked


def extract_payroll_pdfs(paths: Iterable[str | Path]) -> dict[str, Any]:
    """Extract text locally and return candidate rows with document/page provenance."""
    rows: list[dict[str, Any]] = []
    issues: list[str] = []
    for value in paths:
        path = Path(value)
        if not path.is_file():
            issues.append(f"{path.name}: file not found; add rows manually or select another file.")
            continue
        try:
            reader = PdfReader(str(path), strict=False)
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception:  # noqa: BLE001 - malformed/encrypted PDFs vary by pypdf version
                    issues.append(f"{path.name}: could not read this protected PDF; enter its payroll manually.")
                    continue
        except Exception:  # noqa: BLE001 - report user-friendly error for malformed PDFs
            issues.append(f"{path.name}: could not read this PDF; enter its payroll manually.")
            continue

        text_pages = 0
        row_count = 0
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:  # noqa: BLE001 - some malformed page streams cannot be decoded
                text = ""
            if not text.strip():
                continue
            text_pages += 1
            for line in text.splitlines():
                candidate = _candidate_from_line(line, path.name, page_number)
                if candidate:
                    rows.append(candidate)
                    row_count += 1
        if not text_pages:
            issues.append(f"{path.name}: no readable text was found (possibly a scanned/image-only PDF). "
                          "Enter payroll manually or use a text-based payroll record.")
        elif not row_count:
            issues.append(f"{path.name}: text was present, but payroll rows could not be reliably identified. "
                          "Review the document and enter rows manually.")
    rows = mark_row_relationships(rows)
    return {"rows": rows, "issues": issues}


def review_window_flags(rows: Iterable[dict[str, Any]], date_of_injury: str) -> list[dict[str, Any]]:
    """Annotate rows against the validated reporting window without removing any."""
    window = form22_reporting_window(date_of_injury)
    result = []
    for row in rows:
        flagged = dict(row)
        work_date = flagged.get("date")
        flagged["outside_window"] = bool(
            work_date and not window["start"] <= str(work_date) <= window["end"]
        )
        result.append(flagged)
    return result
