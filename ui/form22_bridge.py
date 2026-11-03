"""Thin, offline UI bridge around the Form 22 generator."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from generate_form22 import generate  # noqa: E402


def run(payroll: str, doi: str, template: str, output: str) -> dict:
    """Returns {'ok': bool, 'message': str}; never raises for user errors."""
    try:
        payload = generate(payroll, doi, template, output)
    except (OSError, ValueError, KeyError) as exc:
        return {"ok": False, "message": str(exc)}
    return {"ok": True, "message": f"Wrote {output} ({len(payload['checkboxes'])} days checked)"}
