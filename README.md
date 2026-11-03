# NC Form 22 Generator

> **This tool fills Form 22. It does not calculate average weekly wage or compensation rate.**

A local, offline Windows application that fills the North Carolina Industrial Commission
Form 22 (revision 08/2026) from a payroll CSV or JSON file. No payroll, employee or claim data
ever leaves your computer; there is no telemetry.

## For normal users

1. Download `NC-Form-22-Generator-Setup.exe` (from the GitHub Actions "Windows Package" run artifacts or a release).
2. Run it and follow the prompts. No administrator rights are needed; a desktop shortcut is optional.
3. Launch **NC Form 22 Generator** from the Start menu.
4. Click **Browse...** and select your payroll CSV or JSON file.
5. Enter the date of injury as `YYYY-MM-DD`; review the summary shown by **Check payroll**.
6. Click **Generate Form 22**, choose where to save the PDF, then use **Open PDF** or **Show in folder**.

Payroll columns/keys: `date` (YYYY-MM-DD), `amount` (non-negative number), optional `paid_in_full`
(true/false, yes/no, 1/0; blank means true) and `source`. See `examples/`.
The 52 weeks (364 days) before the date of injury are reported; the injury date itself is excluded.
The official Form 22 is bundled in the app; you never need to select it.

## For developers

```bash
pip install -r requirements.txt            # dev + build tools (runtime only: requirements-runtime.txt)
python -m pytest tests -q                  # full suite, including real-template tests
python ui/form22_app.py                    # run the UI from source
python scripts/generate_form22.py --payroll examples/payroll_sample.csv --doi 2026-08-15 \
    --template templates/form22.pdf --output out.pdf          # CLI
```

**Build the executable (Windows):**

```bash
python packaging/make_version_info.py build/version_info.txt
python -m PyInstaller --noconfirm --clean packaging/Form22Generator.spec   # -> dist/Form22Generator.exe
dist/Form22Generator.exe --selftest smoke.pdf                              # headless smoke check
```

Set `FORM22_DEBUG_CONSOLE=1` before building to get a console-enabled debug build. Production
builds are windowed. To brand the exe, add `packaging/app.ico` (picked up automatically if present).

**Build the installer:** install [Inno Setup 6](https://jrsoftware.org/isinfo.php), then
`iscc /DAppVersion=0.9.0 packaging\installer.iss` -> `dist/NC-Form-22-Generator-Setup.exe`
(per-user install, Start menu + optional desktop shortcut, uninstaller, in-place upgrades via a fixed AppId).

**CI:** `.github/workflows/windows-package.yml` runs on `windows-latest`: tests, lint, PyInstaller,
packaged-exe smoke test, Inno Setup, and uploads artifacts `Form22Generator-exe` and
`NC-Form-22-Generator-Setup`. `ci.yml` remains the Linux lint/test job.

**`templates/form22.pdf`** is the official, unmodified Form 22 (08/2026) AcroForm. It is embedded into
the executable by the PyInstaller spec and located at runtime by `scripts/app_paths.py`. The version
lives in `scripts/form22_version.py`.

## Windows acceptance checklist (manual)

Normal: CSV; JSON; DOI crossing a year boundary; explicit paid/unpaid; cents; first (DOI-364) and last
(DOI-1) days. Failures with friendly messages: missing payroll, bad date, unsupported format,
malformed CSV/JSON, negative earnings, invalid `paid_in_full`, missing/corrupt template, unwritable
output. Verify the PDF has exactly two pages, correct DOI, monthly/total earnings with cents, correct
paid-in-full boxes, blank unpaid dates and the unchanged official layout. Most of these are automated in
`tests/test_packaging_and_ui.py` and `tests/test_form22_pipeline.py`.

## License

Proprietary -- All rights reserved.
