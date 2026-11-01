# nc-form22-generator

> Automated generator for North Carolina Form 22 (Wage and Hour Bureau).
>
> ---
>
> ## Overview
>
> `nc-form22-generator` is a cross-platform desktop tool (Tauri/Windows `.exe` + Python alternative) that:
>
> - Maps and populates all AcroForm fields on NC Form 22 PDFs
> - - Parses DOI dates and 52-week wage/hour windows
>   - - Supports optional OCR for scanned PDF sources
>     - - Ships a DPAPI-backed license verifier
>       - - Provides a polished UI scaffold for end-user data entry
>         - - Packages as a signed Windows installer and a standalone Python script
>          
>           - ---
>
> ## Milestone Sequence
>
> | # | Milestone | Status |
> |---|-----------|--------|
> | 1 | Canonical AcroForm field map | Pending |
> | 2 | JS parser (DOI / 52-week module) | Pending |
> | 3 | Python parser (DOI / 52-week module) | Pending |
> | 4 | PDF population engine | Pending |
> | 5 | UI scaffold | Pending |
> | 6 | OCR integration | Pending |
> | 7 | License verifier (DPAPI) | Pending |
> | 8 | Packaging scripts (Tauri + Python) | Pending |
> | 9 | CI pipeline | Pending |
> | 10 | QA and documentation | Pending |
>
> ---
>
> ## Prerequisites
>
> - **Node.js** >= 20 (for JS parser and Tauri build)
> - - **Rust** stable (for Tauri)
>   - - **Python** >= 3.11 (for Python alternative)
>     - - **pdfplumber / pypdf** (PDF parsing)
>       - - **tesseract-ocr** >= 5.0 (optional, OCR path only)
>        
>         - ---
>
> ## Quick Start
>
> ### Tauri / Windows
>
> ```bash
> npm install
> npm run tauri build
> ```
>
> ### Python Alternative
>
> ```bash
> pip install -r requirements.txt
> python src/python/generate_form22.py --input data.json --pdf form22_template.pdf
> ```
>
> ---
>
> ## Project Structure
>
> ```
> nc-form22-generator/
>  .github/workflows/
>     milestone-tracker.yml
>     ci.yml
>  src/js/
>     fieldMap.js
>     doiParser.js
>     weeklyWageCalc.js
>     pdfPopulator.js
>  src/python/
>     field_map.py
>     doi_parser.py
>     weekly_wage_calc.py
>     pdf_populator.py
>     ocr_extractor.py
>     generate_form22.py
>  packaging/build_python_pkg.py
>  scripts/update_status.py
>  tests/js/ and tests/python/
>  README.md
>  STATUS.md
>  status.json
>  status.html
> ```
>
> ---
>
> ## Configuration
>
> | Variable | Description |
> |----------|-------------|
> | `FORM22_TEMPLATE_PATH` | Path to the official NC Form 22 PDF template |
> | `LICENSE_KEY` | DPAPI-protected license key blob |
> | `OCR_ENABLED` | true / false (default: false) |
> | `DIGEST_EMAIL` | Recipient for daily progress digests |
>
> ---
>
> ## Daily Digest
>
> A daily milestone-progress summary is emailed to `michael_a_cannon@hotmail.com` every day at 08:00 EST.
>
> ---
>
> ## License
>
> Proprietary -- All rights reserved.
