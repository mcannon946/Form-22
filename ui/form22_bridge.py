"""Offline bridge between the desktop UI and the Form 22 pipeline.

Every function returns plain dicts and never raises for user-facing problems.
"""
from __future__ import annotations

import csv
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from app_paths import bundled_template  # noqa: E402
from form22_pipeline import build_payload  # noqa: E402
from payroll_importer import import_payroll  # noqa: E402
from payroll_parser import parse_amount, parse_bool, parse_iso_date, form22_reporting_window  # noqa: E402
from pdf_population_engine import populate_pdf  # noqa: E402

TEMPLATE_PROBLEM = ("The bundled Form 22 template is missing or damaged. "
                    "Please reinstall NC Form 22 Generator.")
CUSTOM_TEMPLATE_PROBLEM = ("The selected alternate template is missing, damaged, or is not a "
                           "compatible Form 22. Clear it to use the verified bundled template.")


def _friendly(exc: Exception, stage: str) -> str:
    """Translate an exception into a plain-language message."""
    if isinstance(exc, FileNotFoundError) and stage == "payroll":
        return "The payroll file could not be found. Please choose it again."
    if isinstance(exc, UnicodeDecodeError):
        return "The payroll file is not a readable CSV or JSON text file."
    if isinstance(exc, csv.Error):
        return f"The payroll CSV is malformed: {exc}"
    if isinstance(exc, PermissionError):
        if stage == "output":
            return ("Cannot save to that location. Choose a different folder "
                    "(for example Documents) and make sure the file is not open in another program.")
        return "Permission denied while reading the payroll file."
    if stage == "template" or isinstance(exc, KeyError):
        return TEMPLATE_PROBLEM
    if isinstance(exc, OSError):
        if stage == "output":
            return f"Could not save the PDF: {exc.strerror or exc}"
        return f"Could not read the file: {exc.strerror or exc}"
    return str(exc)


def _check_inputs(payroll: str, doi: str):
    if not payroll or not payroll.strip():
        raise ValueError("Please select a payroll CSV or JSON file.")
    if not doi or not doi.strip():
        raise ValueError("Please enter the date of injury (YYYY-MM-DD).")
    try:
        parse_iso_date(doi.strip(), "date of injury")
    except ValueError as exc:
        raise ValueError("The date of injury is not valid. Use YYYY-MM-DD, for example 2026-08-15.") from exc
    return import_payroll(payroll.strip())


def preview(payroll: str, doi: str) -> dict:
    """Validate inputs and summarise what will be written. Writes nothing."""
    try:
        rows = _check_inputs(payroll, doi)
        payload = build_payload(rows, doi.strip())
    except (OSError, ValueError, KeyError, csv.Error) as exc:
        return {"ok": False, "message": _friendly(exc, "payroll")}
    w = payload["window"]
    in_window = [r for r in rows if w["start"] <= r["date"] <= w["end"]]
    total = sum((Decimal(str(r["amount"])) for r in in_window), Decimal(0))
    paid = len(payload["paid_in_full_dates"])
    lines = [
        f"Rows imported: {len(rows)} ({len(rows) - len(in_window)} outside the reporting period, ignored)",
        f"Reporting period: {w['start']} to {w['end']}",
        f"Rows in period: {len(in_window)}",
        f"Total earnings in period: ${total:,.2f}",
        f"Days marked paid in full: {paid}",
    ]
    if not in_window:
        lines.append("Warning: no payroll rows fall in the reporting period.")
    return {"ok": True, "message": "\n".join(lines), "rows": len(rows),
            "rows_in_window": len(in_window), "paid_days": paid, "total": str(total)}


def run(payroll: str, doi: str, output: str, template: str | None = None) -> dict:
    """Generate the Form 22. Uses the bundled template unless one is given."""
    if not output or not output.strip():
        return {"ok": False, "message": "Please choose where to save the completed PDF."}
    output_path = Path(output.strip())
    if payroll and output_path.resolve() == Path(payroll.strip()).resolve():
        return {"ok": False, "message": "The output file must be different from the payroll file."}
    if output_path.suffix.lower() != ".pdf":
        output_path = output_path.with_suffix(".pdf")
    try:
        rows = _check_inputs(payroll, doi)
        payload = build_payload(rows, doi.strip())
    except (OSError, ValueError, KeyError, csv.Error) as exc:
        return {"ok": False, "message": _friendly(exc, "payroll")}

    template_path = Path(template.strip()) if template and template.strip() else bundled_template()
    template_problem = TEMPLATE_PROBLEM if template_path == bundled_template() else CUSTOM_TEMPLATE_PROBLEM
    if not template_path.is_file():
        return {"ok": False, "message": template_problem}
    try:
        populate_pdf(template_path, output_path, payload)
    except (KeyError, ValueError):
        return {"ok": False, "message": template_problem}
    except OSError as exc:
        return {"ok": False, "message": _friendly(exc, "output")}
    except Exception:  # noqa: BLE001 - pypdf raises its own error types for corrupt PDFs
        return {"ok": False, "message": template_problem}
    return {"ok": True, "output": str(output_path),
            "message": f"Form 22 saved to:\n{output_path}"}


def _reviewed_rows(rows: list[dict], doi: str) -> list[dict]:
    if not rows:
        raise ValueError("Add at least one payroll row before generating Form 22.")
    form22_reporting_window(doi)
    accepted = []
    seen: set[tuple[str, object]] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Payroll row {index} is not valid.")
        if not row.get("include", True):
            continue
        if row.get("review_status") != "Reviewed":
            raise ValueError(f"Review payroll row {index} before generating Form 22.")
        work_date = parse_iso_date(row.get("date"), f"row {index} date")
        amount = parse_amount(row.get("amount"), f"row {index} earnings")
        raw_paid = row.get("paid_in_full")
        if raw_paid is None or raw_paid == "":
            raise ValueError(f"Choose whether payroll row {index} was paid in full.")
        paid = parse_bool(raw_paid, f"row {index} paid-in-full status")
        duplicate_key = (work_date.isoformat(), amount)
        if duplicate_key in seen:
            raise ValueError(
                f"Identical payroll rows are both selected (row {index}). "
                "Exclude or delete a duplicate before continuing."
            )
        seen.add(duplicate_key)
        accepted.append({
            "date": work_date.isoformat(),
            "amount": amount,
            "paid_in_full": paid,
            "source": row.get("source"),
        })
    if not accepted:
        raise ValueError("No payroll rows are selected. Add or include a reviewed row.")
    return accepted


def preview_reviewed(rows: list[dict], doi: str) -> dict:
    """Validate explicitly reviewed rows before presenting the final summary."""
    try:
        accepted = _reviewed_rows(rows, doi)
        payload = build_payload(accepted, doi.strip())
    except (OSError, ValueError, KeyError) as exc:
        return {"ok": False, "message": _friendly(exc, "payroll")}
    window = payload["window"]
    outside = sum(not window["start"] <= row["date"] <= window["end"] for row in accepted)
    total = sum((Decimal(str(amount)) for amount in payload["monthly_totals"].values()), Decimal(0))
    return {
        "ok": True,
        "message": (f"Reviewed rows: {len(accepted)} ({outside} outside the reporting period)\n"
                    f"Reporting period: {window['start']} to {window['end']}\n"
                    f"Rows in period: {len(accepted) - outside}\n"
                    f"Total earnings in period: ${total:,.2f}\n"
                    f"Days marked paid in full: {len(payload['paid_in_full_dates'])}"),
        "rows": len(accepted),
        "rows_in_window": len(accepted) - outside,
        "total": str(total),
    }


def run_reviewed(rows: list[dict], doi: str, output: str, template: str | None = None) -> dict:
    """Generate Form 22 only from rows explicitly accepted in the review screen."""
    if not output or not output.strip():
        return {"ok": False, "message": "Please choose where to save the completed PDF."}
    output_path = Path(output.strip())
    if output_path.suffix.lower() != ".pdf":
        output_path = output_path.with_suffix(".pdf")
    try:
        accepted = _reviewed_rows(rows, doi.strip())
        payload = build_payload(accepted, doi.strip())
    except (OSError, ValueError, KeyError) as exc:
        return {"ok": False, "message": _friendly(exc, "payroll")}
    template_path = Path(template.strip()) if template and template.strip() else bundled_template()
    template_problem = TEMPLATE_PROBLEM if template_path == bundled_template() else CUSTOM_TEMPLATE_PROBLEM
    if not template_path.is_file():
        return {"ok": False, "message": template_problem}
    try:
        populate_pdf(template_path, output_path, payload)
    except (KeyError, ValueError):
        return {"ok": False, "message": template_problem}
    except OSError as exc:
        return {"ok": False, "message": _friendly(exc, "output")}
    except Exception:  # noqa: BLE001 - pypdf raises its own error types for corrupt PDFs
        return {"ok": False, "message": template_problem}
    return {"ok": True, "output": str(output_path),
            "message": f"Form 22 saved to:\n{output_path}"}
