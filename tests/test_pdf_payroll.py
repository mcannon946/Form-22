"""Offline PDF payroll extraction, review flags, and reviewed-generation tests."""
import sys
from datetime import date
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "ui"))

from form22_bridge import preview_reviewed, run_reviewed  # noqa: E402
from form22_day_grid import field_for_date  # noqa: E402
from form22_earnings_fields import MONTH_EARNINGS_FIELDS  # noqa: E402
from pdf_payroll import extract_payroll_pdfs, mark_row_relationships, review_window_flags  # noqa: E402

DOI = "2026-08-15"


def _pdf_string(text):
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_text_pdf(path, page_lines):
    writer = PdfWriter()
    for lines in page_lines:
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        })
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})
        })
        commands = ["BT /F1 10 Tf 50 750 Td"]
        for index, line in enumerate(lines):
            if index:
                commands.append("0 -16 Td")
            commands.append(f"({_pdf_string(line)}) Tj")
        commands.append("ET")
        stream = DecodedStreamObject()
        stream.set_data("\n".join(commands).encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def test_extracts_simple_table_with_page_and_filename_provenance(tmp_path):
    path = make_text_pdf(tmp_path / "simple.pdf", [[
        "Employee: Jordan Example",
        "Work Date  Earnings  Paid in Full",
        "01/05/2026 Regular Pay $1,200.50 Paid in full",
    ]])
    result = extract_payroll_pdfs([path])
    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["date"] == "2026-01-05"
    assert str(row["amount"]) == "1200.50"
    assert row["paid_in_full"] is True
    assert row["provenance"] == {
        "filename": "simple.pdf", "page": 1,
        "snippet": "01/05/2026 Regular Pay $1,200.50 Paid in full",
    }
    assert row["review_status"] == "Needs review"
    assert row["source"] == "simple.pdf, page 1"
    assert not result["issues"]


def test_pay_period_statement_keeps_period_and_unknown_paid_status(tmp_path):
    path = make_text_pdf(tmp_path / "statement.pdf", [[
        "PAY PERIOD: 2026-01-01 through 2026-01-14",
        "Gross earnings for period $2,450.00",
        "Pay period 2026-01-01 to 2026-01-14 Gross earnings $2,450.00",
    ]])
    result = extract_payroll_pdfs([path])
    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["date"] == ""
    assert row["period"] == {"start": "2026-01-01", "end": "2026-01-14"}
    assert str(row["amount"]) == "2450.00"
    assert row["paid_in_full"] is None
    assert row["field_status"] == {
        "date": "Missing", "amount": "Extracted", "paid_in_full": "Missing",
    }


def test_multi_page_report_ignores_irrelevant_headers_and_footers(tmp_path):
    path = make_text_pdf(tmp_path / "report.pdf", [
        ["Confidential Payroll Summary - 2026", "Page 1 of 2",
         "01/03/2026 Overtime $175.00"],
        ["Confidential Payroll Summary - 2026", "Page 2 of 2",
         "01/10/2026 Regular $800.00 Not paid in full"],
    ])
    result = extract_payroll_pdfs([path])
    assert [(row["date"], str(row["amount"])) for row in result["rows"]] == [
        ("2026-01-03", "175.00"), ("2026-01-10", "800.00"),
    ]
    assert [row["provenance"]["page"] for row in result["rows"]] == [1, 2]
    assert result["rows"][1]["paid_in_full"] is False


def test_overlapping_payroll_pdfs_keep_and_mark_duplicates_and_conflicts(tmp_path):
    first = make_text_pdf(tmp_path / "first.pdf", [[
        "01/05/2026 Regular $500.00",
        "01/06/2026 Regular $400.00",
    ]])
    second = make_text_pdf(tmp_path / "second.pdf", [[
        "01/05/2026 Regular $500.00",
        "01/06/2026 Regular $450.00",
    ]])
    rows = extract_payroll_pdfs([first, second])["rows"]
    assert len(rows) == 4
    assert rows[0]["duplicate"] and rows[2]["duplicate"]
    assert rows[2]["duplicate_of"] == 0
    assert rows[1]["conflict"] and rows[3]["conflict"]
    assert rows[0]["provenance"]["filename"] == "first.pdf"
    assert rows[2]["provenance"]["filename"] == "second.pdf"


def test_doi_window_flags_without_discarding_relevant_dates(tmp_path):
    path = make_text_pdf(tmp_path / "window.pdf", [[
        "08/15/2025 Prior year $100.00",
        "08/16/2025 First day $200.00",
        "08/14/2026 Last day $300.00",
        "08/15/2026 Date of injury $400.00",
    ]])
    rows = extract_payroll_pdfs([path])["rows"]
    flagged = review_window_flags(rows, DOI)
    assert len(flagged) == 4
    assert [row["outside_window"] for row in flagged] == [True, False, False, True]


@pytest.mark.parametrize("kind", ["scanned", "malformed"])
def test_unusable_pdf_has_clear_manual_entry_message(tmp_path, kind):
    path = tmp_path / f"{kind}.pdf"
    if kind == "scanned":
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        with path.open("wb") as handle:
            writer.write(handle)
    else:
        path.write_bytes(b"not a PDF")
    result = extract_payroll_pdfs([path])
    assert result["rows"] == []
    assert result["issues"]
    message = " ".join(result["issues"]).lower()
    assert "manually" in message
    if kind == "scanned":
        assert "scanned/image-only" in message
    else:
        assert "could not read" in message


def test_text_without_identifiable_payroll_rows_needs_manual_entry(tmp_path):
    path = make_text_pdf(tmp_path / "header-only.pdf", [["Payroll summary", "Page 1 of 1"]])
    result = extract_payroll_pdfs([path])
    assert result["rows"] == []
    assert "could not be reliably identified" in result["issues"][0]


def test_review_corrected_values_are_the_only_values_sent_to_form22(tmp_path):
    source = make_text_pdf(tmp_path / "correction.pdf", [["01/05/2026 Regular $200.20"]])
    row = extract_payroll_pdfs([source])["rows"][0]
    assert row["paid_in_full"] is None
    row.update({
        "amount": "201.25",
        "paid_in_full": False,
        "review_status": "Reviewed",
    })
    preview = preview_reviewed([row], DOI)
    assert preview["ok"], preview
    output = tmp_path / "reviewed.pdf"
    result = run_reviewed([row], DOI, str(output))
    assert result["ok"], result
    fields = PdfReader(str(output)).get_fields()
    assert (fields[MONTH_EARNINGS_FIELDS[1][0]]["/V"],
            fields[MONTH_EARNINGS_FIELDS[1][1]]["/V"]) == ("201", "25")
    assert fields[field_for_date(date(2026, 1, 5))].get("/V") is None


def test_unknown_paid_status_and_unreviewed_rows_cannot_generate(tmp_path):
    row = {"date": "2026-01-05", "amount": "200.00", "paid_in_full": None,
           "review_status": "Reviewed"}
    assert not preview_reviewed([row], DOI)["ok"]
    row["paid_in_full"] = True
    row["review_status"] = "Needs review"
    result = run_reviewed([row], DOI, str(tmp_path / "no.pdf"))
    assert not result["ok"]
    assert not (tmp_path / "no.pdf").exists()


def test_exact_duplicate_rows_cannot_be_double_counted(tmp_path):
    rows = [
        {"date": "2026-01-05", "amount": "200.00", "paid_in_full": True,
         "review_status": "Reviewed"},
        {"date": "2026-01-05", "amount": "200.0", "paid_in_full": True,
         "review_status": "Reviewed"},
    ]
    assert mark_row_relationships(rows)[0]["duplicate"]
    result = preview_reviewed(rows, DOI)
    assert not result["ok"]
    assert "duplicate" in result["message"].lower()
    rows[1]["include"] = False
    assert preview_reviewed(rows, DOI)["ok"]
