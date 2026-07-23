# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — ساخت TimexEditor.exe برای ویندوز."""

import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(SPEC), ".."))

a = Analysis(
    [os.path.join(ROOT, "attendance_app.pyw")],
    pathex=[ROOT],
    binaries=[],
    datas=[],
    hiddenimports=[
        "app",
        "app.attendance_app",
        "app.attendance_core",
        "app.dnd_support",
        "app.win32_dnd",
        "tkinterdnd2",
        "windnd",
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
    name="TimexEditor",
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
    icon=None,
)
