"""Single source of truth for application name, version and publisher."""
from __future__ import annotations

APP_NAME = "NC Form 22 Generator"
APP_VERSION = "0.9.0"
PUBLISHER = "NC Form 22 Generator Project"
EXE_NAME = "Form22Generator.exe"
INSTALLER_NAME = "NC-Form-22-Generator-Setup.exe"
FORM_REVISION = "08/2026"
COPYRIGHT = "Copyright (c) 2026 NC Form 22 Generator Project"
DESCRIPTION = "Fills the North Carolina Industrial Commission Form 22 offline."


def version_tuple(version: str = APP_VERSION) -> tuple[int, int, int, int]:
    parts = [int(p) for p in version.split(".")]
    if not 1 <= len(parts) <= 4:
        raise ValueError(f"Invalid version: {version!r}")
    return tuple(parts + [0] * (4 - len(parts)))  # type: ignore[return-value]


if __name__ == "__main__":
    print(APP_VERSION)
