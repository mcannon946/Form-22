"""Entry point for NC Form 22 Generator (Form22Generator.exe)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from form22_bridge import run  # noqa: E402

SELFTEST_CSV = "date,amount,paid_in_full\n2026-01-15,1200.50,true\n2026-02-01,800.25,false\n"
APP_MUTEX_NAME = r"Local\NCForm22Generator-6B7C1E52-3F0A-4C57-9E0D-4F22A1C9B022"
_APP_MUTEX_HANDLE = None


def _hold_app_mutex() -> None:
    """Keep the named Windows mutex alive so Setup can detect this app reliably."""
    global _APP_MUTEX_HANDLE
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    create_mutex = ctypes.WinDLL("kernel32", use_last_error=True).CreateMutexW
    create_mutex.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
    create_mutex.restype = wintypes.HANDLE
    _APP_MUTEX_HANDLE = create_mutex(None, False, APP_MUTEX_NAME)
    if not _APP_MUTEX_HANDLE:
        raise OSError(ctypes.get_last_error(), "Could not register the application with Windows Setup.")


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
    _hold_app_mutex()
    from form22_gui import App

    App().mainloop()


if __name__ == "__main__":
    main()
