# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['standalone_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('data', 'data'),
    ],
    hiddenimports=['pandas', 'numpy', 'openpyxl'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['matplotlib', 'PIL', 'tkinter'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='氧烛分析系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)
