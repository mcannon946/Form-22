"""Write the Windows version-resource file used by PyInstaller."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import form22_version as v  # noqa: E402

TEMPLATE = """VSVersionInfo(
  ffi=FixedFileInfo(filevers={tup}, prodvers={tup}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', '{publisher}'),
      StringStruct('FileDescription', '{app}'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', 'Form22Generator'),
      StringStruct('LegalCopyright', '{copyright}'),
      StringStruct('OriginalFilename', '{exe}'),
      StringStruct('ProductName', '{app}'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def render() -> str:
    return TEMPLATE.format(tup=v.version_tuple(), publisher=v.PUBLISHER, app=v.APP_NAME,
                           version=v.APP_VERSION, copyright=v.COPYRIGHT, exe=v.EXE_NAME)


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "build/version_info.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
