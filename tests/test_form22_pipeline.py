"""Tests for the Form 22 pipeline. Uses a synthetic AcroForm template that mirrors the
official field names; if templates/form22.pdf exists it is also exercised."""
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (ArrayObject, DictionaryObject, FloatObject, NameObject,
                           NumberObject, TextStringObject)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from form22_day_grid import MONTH_SUFFIX, build_day_grid_map, field_for_date  # noqa: E402
from form22_earnings_fields import MONTH_EARNINGS_FIELDS, TOTAL_EARNINGS_FIELDS  # noqa: E402
from form22_pipeline import build_payload  # noqa: E402
from generate_form22 import main as cli_main  # noqa: E402
from payroll_importer import import_payroll  # noqa: E402
from payroll_parser import form22_reporting_window, parse_bool, rows_for_form22  # noqa: E402
from pdf_population_engine import populate_pdf  # noqa: E402

DOI = "2026-08-15"


def row(d, amount="100.00", paid=True):
    return {"date": d, "amount": amount, "paid_in_full": paid}


# ---- window -----------------------------------------------------------
def test_window_bounds():
    w = form22_reporting_window(DOI)
    assert (w["start"], w["end"]) == ("2025-08-16", "2026-08-14")
    assert (date.fromisoformat(w["end"]) - date.fromisoformat(w["start"])).days + 1 == 364


def test_doi_excluded_and_edges_included():
    rows = [row("2025-08-15"), row("2025-08-16"), row("2026-08-14"), row(DOI)]
    got = [r["date"] for r in rows_for_form22(rows, DOI)]
    assert got == ["2025-08-16", "2026-08-14"]


def test_year_boundary():
    rows = [row("2025-12-31"), row("2026-01-01")]
    assert len(rows_for_form22(rows, "2026-01-02")) == 2
    w = form22_reporting_window("2026-01-02")
    assert w["start"] == "2025-01-03" and w["end"] == "2026-01-01"


@pytest.mark.parametrize("bad", ["2026-13-01", "08/15/2026", "2026-8-15", "", None, "2026-02-30"])
def test_invalid_doi(bad):
    with pytest.raises(ValueError):
        form22_reporting_window(bad)


def test_invalid_row_date():
    with pytest.raises(ValueError):
        rows_for_form22([row("2026-02-30")], DOI)


@pytest.mark.parametrize("bad", ["-1", "abc", "nan", "inf", "-Infinity", float("nan"), None])
def test_bad_amounts(bad):
    with pytest.raises(ValueError):
        rows_for_form22([row("2026-01-01", bad)], DOI)


def test_false_stays_false():
    for text in ("false", "False", " NO ", "0", "not paid in full"):
        assert parse_bool(text) is False
    assert rows_for_form22([row("2026-01-01", paid="false")], DOI)[0]["paid_in_full"] is False
    assert parse_bool("TRUE") is True


@pytest.mark.parametrize("bad", ["maybe", "2", "nope"])
def test_invalid_paid_in_full(bad):
    with pytest.raises(ValueError):
        rows_for_form22([row("2026-01-01", paid=bad)], DOI)


# ---- importer ---------------------------------------------------------
def test_import_csv_and_json(tmp_path):
    c = tmp_path / "p.csv"
    c.write_text("date,amount,paid_in_full,source\n2026-01-01,10.5,false,a\n2026-01-02,5,,\n")
    rows = import_payroll(c)
    assert rows[0]["paid_in_full"] is False and rows[1]["paid_in_full"] is True
    assert rows[0]["amount"] == Decimal("10.5") and rows[0]["source"] == "a"
    j = tmp_path / "p.json"
    j.write_text(json.dumps([{"date": "2026-01-01", "amount": "1.00", "paid_in_full": "no"}]))
    assert import_payroll(j)[0]["paid_in_full"] is False


def test_import_rejections(tmp_path):
    with pytest.raises(FileNotFoundError):
        import_payroll(tmp_path / "missing.csv")
    t = tmp_path / "p.txt"
    t.write_text("x")
    with pytest.raises(ValueError):
        import_payroll(t)
    cases = {
        "nodate.csv": "amount\n1\n",
        "negative.csv": "date,amount\n2026-01-01,-5\n",
        "baddate.csv": "date,amount\n2026-99-01,5\n",
        "badpaid.csv": "date,amount,paid_in_full\n2026-01-01,5,maybe\n",
    }
    for name, body in cases.items():
        f = tmp_path / name
        f.write_text(body)
        with pytest.raises(ValueError):
            import_payroll(f)
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    with pytest.raises(ValueError):
        import_payroll(bad)


def test_examples_import():
    assert import_payroll(ROOT / "examples" / "payroll_sample.csv")
    assert import_payroll(ROOT / "examples" / "payroll_sample.json")


# ---- pipeline ---------------------------------------------------------
def test_payload_totals_and_checkboxes():
    rows = [row("2025-12-31", "1000.10"), row("2026-01-05", "200.20"),
            row("2026-01-06", "0.05", paid=False), row(DOI, "999"), row("2025-08-15", "999")]
    p = build_payload(rows, DOI)
    t = p["text_fields"]
    assert (t[MONTH_EARNINGS_FIELDS[12][0]], t[MONTH_EARNINGS_FIELDS[12][1]]) == ("1000", "10")
    assert (t[MONTH_EARNINGS_FIELDS[1][0]], t[MONTH_EARNINGS_FIELDS[1][1]]) == ("200", "25")
    assert (t[TOTAL_EARNINGS_FIELDS[0]], t[TOTAL_EARNINGS_FIELDS[1]]) == ("1200", "35")
    assert p["paid_in_full_dates"] == ["2025-12-31", "2026-01-05"]
    assert field_for_date(date(2026, 1, 6)) not in p["checkboxes"]
    assert sorted(p["checkboxes"]) == sorted([field_for_date(date(2025, 12, 31)), field_for_date(date(2026, 1, 5))])
    assert not any("aww" in k.lower() or "rate" in k.lower() for k in p["text_fields"])


# ---- PDF --------------------------------------------------------------
def make_template(path):
    text_names = {"Date of Injury", "Employees Name", *TOTAL_EARNINGS_FIELDS}
    for d, c in MONTH_EARNINGS_FIELDS.values():
        text_names.update((d, c))
    boxes = []
    for m in range(1, 13):
        for d in range(1, 32):
            boxes.append(f"Check Box{d if d == 1 else d + 1}.{MONTH_SUFFIX[m]}")
    w = PdfWriter()
    pages = [w.add_blank_page(612, 792), w.add_blank_page(612, 792)]
    fields = ArrayObject()
    for i, name in enumerate(sorted(text_names) + boxes):
        is_box = name.startswith("Check Box")
        widget = DictionaryObject({
            NameObject("/Type"): NameObject("/Annot"), NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/FT"): NameObject("/Btn" if is_box else "/Tx"),
            NameObject("/T"): TextStringObject(name),
            NameObject("/Rect"): ArrayObject([FloatObject(10), FloatObject(10 + i % 700), FloatObject(20),
                                              FloatObject(20 + i % 700)]),
        })
        if is_box:
            widget[NameObject("/AS")] = NameObject("/Off")
            widget[NameObject("/AP")] = DictionaryObject({NameObject("/N"): DictionaryObject({
                NameObject("/Yes"): w._add_object(DictionaryObject()),
                NameObject("/Off"): w._add_object(DictionaryObject())})})
        ref = w._add_object(widget)
        fields.append(ref)
        page = pages[0 if i % 2 == 0 else 1]
        page.setdefault(NameObject("/Annots"), ArrayObject()).append(ref)
    w._root_object[NameObject("/AcroForm")] = DictionaryObject({NameObject("/Fields"): fields})
    with open(path, "wb") as fh:
        w.write(fh)


@pytest.fixture(scope="module")
def template(tmp_path_factory):
    official = ROOT / "templates" / "form22.pdf"
    if official.is_file():
        return official
    p = tmp_path_factory.mktemp("tpl") / "form22_test_template.pdf"
    make_template(p)
    return p


def test_generated_pdf(template, tmp_path):
    csv_path = tmp_path / "p.csv"
    csv_path.write_text("date,amount,paid_in_full\n2026-01-05,200.20,true\n2026-01-06,0.05,false\n"
                        "2025-12-31,1000.10,TRUE\n2026-08-15,500,true\n")
    fields_path = tmp_path / "fields.json"
    fields_path.write_text(json.dumps({"Employees Name": "Test Employee"}))
    out = tmp_path / "out.pdf"
    assert cli_main(["--payroll", str(csv_path), "--doi", DOI, "--template", str(template),
                     "--output", str(out), "--fields", str(fields_path)]) == 0
    reader = PdfReader(str(out))
    assert len(reader.pages) == 2
    f = reader.get_fields()
    assert f["Date of Injury"]["/V"] == "08/15/2026"
    assert f["Employees Name"]["/V"] == "Test Employee"
    assert (f[MONTH_EARNINGS_FIELDS[1][0]]["/V"], f[MONTH_EARNINGS_FIELDS[1][1]]["/V"]) == ("200", "25")
    assert (f[TOTAL_EARNINGS_FIELDS[0]]["/V"], f[TOTAL_EARNINGS_FIELDS[1]]["/V"]) == ("1200", "35")
    assert f[field_for_date(date(2026, 1, 5))]["/V"] == "/Yes"
    assert f[field_for_date(date(2025, 12, 31))]["/V"] == "/Yes"
    assert f[field_for_date(date(2026, 1, 6))].get("/V") in (None, "/Off")
    assert f[field_for_date(date(2026, 8, 15))].get("/V") in (None, "/Off")


def test_all_monthly_earnings_fields_populate(template, tmp_path):
    rows = [
        row(date(2025 if month >= 9 else 2026, month, 1).isoformat(), "100.01", paid=False)
        for month in range(1, 13)
    ]
    payload = build_payload(rows, DOI)
    out = tmp_path / "all_months.pdf"
    populate_pdf(template, out, payload)

    fields = PdfReader(str(out)).get_fields()
    for month, (dollars, cents) in MONTH_EARNINGS_FIELDS.items():
        assert (fields[dollars]["/V"], fields[cents]["/V"]) == ("100", "01")
        assert fields[field_for_date(date(2025 if month >= 9 else 2026, month, 1))].get("/V") in (
            None, "/Off"
        )
    assert (fields[TOTAL_EARNINGS_FIELDS[0]]["/V"], fields[TOTAL_EARNINGS_FIELDS[1]]["/V"]) == (
        "1200", "12"
    )


def test_calendar_checkbox_fields_exist(template):
    fields = PdfReader(str(template)).get_fields()
    day_grid = build_day_grid_map(str(template), 2026)
    assert len(day_grid) == 365
    assert all(fields[name]["/FT"] == "/Btn" for name in day_grid.values())


def test_engine_rejects_unknown_field_and_missing_template(template, tmp_path):
    with pytest.raises(KeyError):
        populate_pdf(template, tmp_path / "o.pdf", {"text_fields": {"No Such Field": "x"}})
    with pytest.raises(FileNotFoundError):
        populate_pdf(tmp_path / "nope.pdf", tmp_path / "o.pdf", {})


def test_cli_errors(template, tmp_path, capsys):
    assert cli_main(["--payroll", str(tmp_path / "missing.csv"), "--doi", DOI,
                     "--template", str(template), "--output", str(tmp_path / "o.pdf")]) == 1
    assert "error" in capsys.readouterr().err
