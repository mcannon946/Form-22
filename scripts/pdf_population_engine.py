"""NC Form 22 PDF population engine (baseline).

Fills verified AcroForm text fields in the official 08/2026 template.
Day-grid checkbox mapping is intentionally handled separately after canonical
month/day mapping is finalized.
"""
from __future__ import annotations

from pathlib import Path
from typing import Mapping, Any
from pypdf import PdfReader, PdfWriter

ALLOWED_TEXT_FIELDS = {
    "IC File", "Emp Code", "Carrier Code", "Carrier File", "Employees Name",
    "Address", "Employer_s_Address", "City", "Employers_State", "Employers_Zip",
    "Insurance Carrier", "Carrier_s_Address", "City_2", "Carriers_State",
    "Carriers_Zip", "Date of Injury", "Name of Employee", "Day", "Employer",
}


def populate_form22(template: str | Path, output: str | Path, values: Mapping[str, Any]) -> Path:
    template = Path(template)
    output = Path(output)
    reader = PdfReader(str(template))
    fields = reader.get_fields() or {}
    unknown_pdf_fields = [name for name in values if name not in fields]
    if unknown_pdf_fields:
        raise KeyError(f"Unknown PDF fields: {', '.join(unknown_pdf_fields)}")
    unsupported = [name for name in values if name not in ALLOWED_TEXT_FIELDS]
    if unsupported:
        raise ValueError(f"Fields not enabled in baseline engine: {', '.join(unsupported)}")

    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    clean = {name: '' if value is None else str(value) for name, value in values.items()}
    for page in writer.pages:
        writer.update_page_form_field_values(page, clean, auto_regenerate=True)
    with output.open('wb') as fh:
        writer.write(fh)
    return output
