# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['一键运行全部.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('data', 'data'),
        ('modules', 'modules'),
        ('简单分析程序.py', '.'),
        ('评分排名程序.py', '.'),
        ('对比分析程序.py', '.'),
        ('网页系统.py', '.'),
    ],
    hiddenimports=[
        'pandas',
        'numpy',
        'openpyxl',
        'scipy',
        'matplotlib',
        'streamlit',
        'plotly'
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
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
    console=True,
    icon=None,
)
