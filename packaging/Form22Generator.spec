# PyInstaller spec. Build from the repo root:  pyinstaller packaging/Form22Generator.spec
# Set FORM22_DEBUG_CONSOLE=1 for a console-enabled debug build (shows tracebacks).
import os
from pathlib import Path

root = Path(SPECPATH).parent
debug = os.environ.get("FORM22_DEBUG_CONSOLE") == "1"
version_file = root / "build" / "version_info.txt"
icon_file = root / "packaging" / "app.ico"  # optional: add an .ico here to brand the exe

a = Analysis(
    [str(root / "ui" / "form22_app.py")],
    pathex=[str(root / "scripts"), str(root / "ui")],
    datas=[(str(root / "templates" / "form22.pdf"), "templates")],
    hiddenimports=["form22_gui"],
    excludes=["pytest", "numpy", "PIL", "cryptography"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="Form22Generator",
    console=debug,
    debug=False,
    upx=False,
    version=str(version_file) if version_file.is_file() else None,
    icon=str(icon_file) if icon_file.is_file() else None,
)
