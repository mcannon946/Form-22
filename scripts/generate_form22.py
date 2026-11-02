"""Generate a populated NC Form 22 from normalized payroll JSON.

This is an orchestration/CLI layer only. It does not calculate AWW or
compensation rate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from form22_pipeline import prepare_form22_payload
from pdf_population_engine import populate_form22


def generate_form22(template: str | Path, output: str | Path, payroll_rows, date_of_injury: str) -> Path:
    payload = prepare_form22_payload(payroll_rows, date_of_injury)
    return populate_form22(
        template,
        output,
        values=payload['values'],
        paid_in_full_dates=payload['paid_in_full_dates'],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description='Populate NC Form 22 from normalized payroll JSON.')
    parser.add_argument('--template', required=True, help='Path to blank NC Form 22 PDF')
    parser.add_argument('--payroll', required=True, help='Path to JSON array of normalized payroll rows')
    parser.add_argument('--doi', required=True, help='Date of injury in YYYY-MM-DD format')
    parser.add_argument('--output', required=True, help='Output PDF path')
    args = parser.parse_args()

    rows = json.loads(Path(args.payroll).read_text(encoding='utf-8'))
    if not isinstance(rows, list):
        raise TypeError('payroll JSON must contain an array of rows')
    generate_form22(args.template, args.output, rows, args.doi)


if __name__ == '__main__':
    main()
