# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

sys.path.insert(0, str(Path(SPECPATH).parent))

from version import __version__


def _version_info_file() -> str:
    parts = [int(part) for part in __version__.split(".")]
    while len(parts) < 4:
        parts.append(0)
    path = Path(SPECPATH).parent / "file_version_info.txt"
    path.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({parts[0]}, {parts[1]}, {parts[2]}, {parts[3]}),
    prodvers=({parts[0]}, {parts[1]}, {parts[2]}, {parts[3]}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'ChatList'),
          StringStruct('FileDescription', 'ChatList'),
          StringStruct('FileVersion', '{__version__}'),
          StringStruct('InternalName', '4-ChatList'),
          StringStruct('OriginalFilename', '4-ChatList-{__version__}.exe'),
          StringStruct('ProductName', 'ChatList'),
          StringStruct('ProductVersion', '{__version__}'),
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
    )
    return str(path)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/chatlist.ico', 'assets'), ('assets/chatlist-icon.png', 'assets')],
    hiddenimports=[
        'db',
        'models',
        'network',
        'dialogs',
        'workers',
        'export_utils',
        'env_config',
        'themes',
        'app_icon',
        'version',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f'4-ChatList-{__version__}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/chatlist.ico',
    version=_version_info_file(),
)
