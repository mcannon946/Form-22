"""Entry point for NC Form 22 Generator (Form22Generator.exe)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from form22_bridge import run  # noqa: E402

SELFTEST_CSV = "date,amount,paid_in_full\n2026-01-15,1200.50,true\n2026-02-01,800.25,false\n"


def selftest(output: str) -> int:
    """Headless packaging smoke check: generates a PDF from the bundled template."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        payroll = Path(tmp) / "payroll.csv"
        payroll.write_text(SELFTEST_CSV, encoding="utf-8")
        return 0 if run(str(payroll), "2026-08-15", output)["ok"] else 1


def main() -> None:
    if "--selftest" in sys.argv:
        idx = sys.argv.index("--selftest")
        sys.exit(selftest(sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "selftest.pdf"))
    from form22_gui import App

    App().mainloop()


if __name__ == "__main__":
    main()
