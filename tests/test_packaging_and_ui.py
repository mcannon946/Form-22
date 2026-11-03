"""Packaging, resource-path, version and UI-bridge tests (real official template)."""
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "ui"))
sys.path.insert(0, str(ROOT / "packaging"))

import app_paths  # noqa: E402
import form22_version as ver  # noqa: E402
import make_version_info  # noqa: E402
from form22_bridge import preview, run  # noqa: E402
from form22_day_grid import field_for_date  # noqa: E402
from form22_earnings_fields import MONTH_EARNINGS_FIELDS, TOTAL_EARNINGS_FIELDS  # noqa: E402

DOI = "2026-08-15"


def write_csv(tmp_path, body, name="p.csv"):
    p = tmp_path / name
    p.write_text("date,amount,paid_in_full\n" + body, encoding="utf-8")
    return str(p)


# ---- resource discovery ----------------------------------------------
def test_source_mode_template():
    assert not app_paths.is_frozen()
    assert app_paths.bundled_template() == ROOT / "templates" / "form22.pdf"
    assert app_paths.bundled_template().is_file()


def test_frozen_mode_template(monkeypatch, tmp_path):
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "form22.pdf").write_bytes(b"x")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert app_paths.is_frozen()
    assert app_paths.bundled_template() == tmp_path / "templates" / "form22.pdf"
    assert app_paths.bundled_template().is_file()


def test_default_output_dir_not_install_dir():
    assert not str(app_paths.default_output_dir()).startswith(str(ROOT))


# ---- version / packaging config --------------------------------------
def test_version_info():
    assert ver.APP_NAME == "NC Form 22 Generator"
    assert ver.APP_VERSION == "0.9.0"
    assert ver.version_tuple() == (0, 9, 0, 0)
    text = make_version_info.render()
    assert "ProductName', 'NC Form 22 Generator'" in text
    assert "FileVersion', '0.9.0'" in text
    assert "filevers=(0, 9, 0, 0)" in text


def test_packaging_config_sanity():
    spec = (ROOT / "packaging" / "Form22Generator.spec").read_text()
    assert 'name="Form22Generator"' in spec
    assert "templates" in spec and "form22.pdf" in spec
    assert "console=debug" in spec
    iss = (ROOT / "packaging" / "installer.iss").read_text()
    assert "PrivilegesRequired=lowest" in iss
    assert "OutputBaseFilename=NC-Form-22-Generator-Setup" in iss
    assert "Form22Generator.exe" in iss
    assert f'"{ver.APP_VERSION}"' in iss
    assert re.search(r"AppId=\{\{[0-9A-F-]{36}\}", iss)
    runtime = (ROOT / "requirements-runtime.txt").read_text().lower()
    assert "pypdf" in runtime
    assert not any(w in runtime for w in ("tesseract", "pyinstaller", "requests", "sentry"))


def test_no_empty_source_files():
    skip = {".git", "node_modules", "__pycache__", ".pytest_cache", ".venv"}
    empties = [p for p in ROOT.rglob("*")
               if p.is_file() and not skip.intersection(p.parts) and p.stat().st_size == 0
               and p.suffix in {".py", ".yml", ".iss", ".spec", ".md", ".txt", ".pdf"}]
    assert empties == []


def test_no_aww_or_rate_calculation_in_ui():
    for f in (ROOT / "ui").glob("*.py"):
        text = f.read_text().lower()
        assert "def aww" not in text and "compensation_rate" not in text


# ---- bridge: normal -------------------------------------------------
def test_bridge_generates_real_pdf_csv(tmp_path):
    src = write_csv(tmp_path, "2025-08-16,10.05,true\n2026-08-14,0.95,true\n2025-12-31,1000.10,false\n"
                              "2026-01-01,200.20,true\n2025-08-15,999,true\n2026-08-15,999,true\n")
    pv = preview(src, DOI)
    assert pv["ok"] and pv["rows_in_window"] == 4 and pv["paid_days"] == 3
    out = tmp_path / "out.pdf"
    res = run(src, DOI, str(out))
    assert res["ok"], res
    reader = PdfReader(str(out))
    assert len(reader.pages) == 2
    f = reader.get_fields()
    assert f["Date of Injury"]["/V"] == "08/15/2026"
    assert (f[MONTH_EARNINGS_FIELDS[8][0]]["/V"], f[MONTH_EARNINGS_FIELDS[8][1]]["/V"]) == ("11", "00")
    assert (f[MONTH_EARNINGS_FIELDS[12][0]]["/V"], f[MONTH_EARNINGS_FIELDS[12][1]]["/V"]) == ("1000", "10")
    assert (f[TOTAL_EARNINGS_FIELDS[0]]["/V"], f[TOTAL_EARNINGS_FIELDS[1]]["/V"]) == ("1211", "30")
    for d, checked in [(date(2025, 8, 16), True), (date(2026, 8, 14), True), (date(2026, 1, 1), True),
                       (date(2025, 12, 31), False), (date(2025, 8, 15), False), (date(2026, 8, 15), False)]:
        v = f[field_for_date(d)].get("/V")
        assert (v == "/Yes") is checked, d
    assert "STATEMENT OF DAYS WORKED" in reader.pages[0].extract_text()


def test_bridge_json_and_appends_pdf_suffix(tmp_path):
    src = tmp_path / "p.json"
    src.write_text('[{"date": "2026-01-15", "amount": 5.5, "paid_in_full": "no"}]')
    res = run(str(src), DOI, str(tmp_path / "result"))
    assert res["ok"] and res["output"].endswith("result.pdf")
    assert (tmp_path / "result.pdf").is_file()


def test_bridge_year_boundary_doi(tmp_path):
    src = write_csv(tmp_path, "2025-12-20,50.00,true\n2024-12-31,70.00,true\n")
    out = tmp_path / "o.pdf"
    assert run(src, "2026-01-10", str(out))["ok"]
    f = PdfReader(str(out)).get_fields()
    assert f["Date of Injury"]["/V"] == "01/10/2026"
    assert f[TOTAL_EARNINGS_FIELDS[0]]["/V"] == "50"


# ---- bridge: failures -----------------------------------------------
@pytest.mark.parametrize("payroll_name,body,doi,fragment", [
    (None, None, DOI, "select a payroll"),
    ("missing.csv", None, DOI, "could not be found"),
    ("p.csv", "2026-01-01,5,true\n", "2026-13-40", "date of injury"),
    ("p.csv", "2026-01-01,5,true\n", "", "date of injury"),
    ("p.txt", "x", DOI, "Unsupported"),
    ("p.csv", "2026-01-01,-5,true\n", DOI, "negative"),
    ("p.csv", "2026-01-01,nan,true\n", DOI, "finite"),
    ("p.csv", "2026-01-01,5,maybe\n", DOI, "paid_in_full"),
    ("p.csv", "not-a-date,5,true\n", DOI, "date"),
])
def test_bridge_failures(tmp_path, payroll_name, body, doi, fragment):
    if payroll_name is None:
        path = ""
    else:
        path = str(tmp_path / payroll_name)
        if body is not None:
            content = ("date,amount,paid_in_full\n" + body) if payroll_name.endswith(".csv") else body
            (tmp_path / payroll_name).write_text(content)
    out = tmp_path / "o.pdf"
    for res in (preview(path, doi), run(path, doi, str(out))):
        assert not res["ok"] and fragment.lower() in res["message"].lower(), res
        assert "Traceback" not in res["message"]
    assert not out.exists()


def test_bridge_malformed_json_and_csv(tmp_path):
    bad = tmp_path / "b.json"
    bad.write_text("{not json")
    res = run(str(bad), DOI, str(tmp_path / "o.pdf"))
    assert not res["ok"] and "json" in res["message"].lower()
    nocols = tmp_path / "c.csv"
    nocols.write_text("foo,bar\n1,2\n")
    res = run(str(nocols), DOI, str(tmp_path / "o.pdf"))
    assert not res["ok"] and "missing required column" in res["message"]
    binary = tmp_path / "d.csv"
    binary.write_bytes(b"\xff\xfe\x00\x80\x81")
    assert not run(str(binary), DOI, str(tmp_path / "o.pdf"))["ok"]


def test_bridge_missing_bundled_template(tmp_path, monkeypatch):
    import form22_bridge
    src = write_csv(tmp_path, "2026-01-01,5,true\n")
    monkeypatch.setattr(form22_bridge, "bundled_template", lambda: tmp_path / "nope.pdf")
    res = run(src, DOI, str(tmp_path / "o.pdf"))
    assert not res["ok"] and "reinstall" in res["message"]


def test_bridge_corrupt_template(tmp_path, monkeypatch):
    import form22_bridge
    src = write_csv(tmp_path, "2026-01-01,5,true\n")
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 garbage")
    monkeypatch.setattr(form22_bridge, "bundled_template", lambda: bad)
    res = run(src, DOI, str(tmp_path / "o.pdf"))
    assert not res["ok"] and "reinstall" in res["message"]
    # alternate template gets distinct wording
    alt = tmp_path / "alt.pdf"
    alt.write_bytes(b"%PDF-1.4 garbage")
    res = run(src, DOI, str(tmp_path / "o.pdf"), template=str(alt))
    assert not res["ok"] and "alternate template" in res["message"]


def test_bridge_unwritable_output(tmp_path):
    src = write_csv(tmp_path, "2026-01-01,5,true\n")
    blocker = tmp_path / "file"
    blocker.write_text("x")
    res = run(src, DOI, str(blocker / "sub" / "o.pdf"))
    assert not res["ok"] and "save" in res["message"].lower()
    assert not run(src, DOI, "")["ok"]
    assert not run(src, DOI, src)["ok"]


def test_selftest_entrypoint(tmp_path):
    out = tmp_path / "self.pdf"
    r = subprocess.run([sys.executable, str(ROOT / "ui" / "form22_app.py"), "--selftest", str(out)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert len(PdfReader(str(out)).pages) == 2
