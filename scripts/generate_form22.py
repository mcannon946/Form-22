"""End-to-end CLI: payroll CSV/JSON + date of injury -> filled Form 22 PDF.

Runs fully offline. Does not calculate AWW or compensation rate.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from form22_pipeline import build_payload  # noqa: E402
from payroll_importer import import_payroll  # noqa: E402
from pdf_population_engine import populate_pdf  # noqa: E402


def generate(payroll: str, doi: str, template: str, output: str, fields_json: str | None = None) -> dict:
    extra = {}
    if fields_json:
        extra = json.loads(Path(fields_json).read_text(encoding="utf-8"))
        if not isinstance(extra, dict):
            raise ValueError("--fields must be a JSON object of field name -> text")
    payload = build_payload(import_payroll(payroll), doi, extra)
    populate_pdf(template, output, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate a populated NC Form 22 PDF.")
    p.add_argument("--payroll", required=True, help="payroll .csv or .json")
    p.add_argument("--doi", required=True, help="date of injury, YYYY-MM-DD")
    p.add_argument("--template", required=True, help="official Form 22 PDF template")
    p.add_argument("--output", required=True, help="output PDF path")
    p.add_argument("--fields", help="optional JSON of extra text fields (exact PDF field names)")
    args = p.parse_args(argv)
    try:
        payload = generate(args.payroll, args.doi, args.template, args.output, args.fields)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    w = payload["window"]
    print(f"Wrote {args.output} (window {w['start']} to {w['end']}; "
          f"{len(payload['checkboxes'])} paid-in-full days checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
