"""Locate bundled resources in source checkouts and PyInstaller builds."""
from __future__ import annotations

import sys
from pathlib import Path

TEMPLATE_RELATIVE = Path("templates") / "form22.pdf"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[1]


def bundled_template(root: Path | None = None) -> Path:
    return (root if root is not None else resource_root()) / TEMPLATE_RELATIVE


def default_output_dir() -> Path:
    """User's Documents folder (never the install directory)."""
    docs = Path.home() / "Documents"
    return docs if docs.is_dir() else Path.home()
