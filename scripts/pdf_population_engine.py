"""Fill the official Form 22 AcroForm template locally with pypdf.

The original two-page template is cloned, never redrawn or replaced.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject

EXPECTED_PAGES = 2


def _widget_on_state(annot: Any) -> str:
    ap = annot.get("/AP")
    if ap is not None:
        normal = ap.get_object().get("/N")
        if normal is not None:
            states = [str(k) for k in normal.get_object().keys() if str(k) != "/Off"]
            if states:
                return states[0]
    return "/Yes"


def validate_fields(template: str | Path, text_fields: Mapping[str, str], checkboxes: Iterable[str]) -> None:
    fields = PdfReader(str(template)).get_fields() or {}
    missing = [n for n in list(text_fields) + list(checkboxes) if n not in fields]
    if missing:
        raise KeyError(f"Field(s) not found in PDF template: {', '.join(sorted(set(missing)))}")
    wrong = [n for n in checkboxes if fields[n].get("/FT") != "/Btn"]
    if wrong:
        raise ValueError(f"Not checkbox fields: {', '.join(sorted(wrong))}")
    wrong = [n for n in text_fields if fields[n].get("/FT") != "/Tx"]
    if wrong:
        raise ValueError(f"Not text fields: {', '.join(sorted(wrong))}")


def populate_pdf(template: str | Path, output: str | Path, payload: Mapping[str, Any]) -> Path:
    template, output = Path(template), Path(output)
    if not template.is_file():
        raise FileNotFoundError(f"Form 22 template not found: {template}")
    text_fields = {k: str(v) for k, v in payload.get("text_fields", {}).items()}
    checkboxes = list(payload.get("checkboxes", []))
    validate_fields(template, text_fields, checkboxes)

    writer = PdfWriter(clone_from=str(template))
    if len(writer.pages) != EXPECTED_PAGES:
        raise ValueError(f"Template must have {EXPECTED_PAGES} pages, found {len(writer.pages)}")
    wanted = set(checkboxes)
    for page in writer.pages:
        if text_fields:
            writer.update_page_form_field_values(page, text_fields, auto_regenerate=False)
        for annot_ref in page.get("/Annots", []) or []:
            annot = annot_ref.get_object()
            parent = annot.get("/Parent")
            name = annot.get("/T")
            if name is None and parent is not None:
                name = parent.get_object().get("/T")
            if name is None or str(name) not in wanted:
                continue
            state = _widget_on_state(annot)
            annot[NameObject("/AS")] = NameObject(state)
            target = annot if "/T" in annot else parent.get_object()
            target[NameObject("/V")] = NameObject(state)
    writer.set_need_appearances_writer(True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        writer.write(handle)
    return output
