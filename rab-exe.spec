# rab-exe.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['rab-exe.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('_internal/webull_setup.py', '_internal'),
        ('currentArbsRobinhood.json', '.'),
        ('currentArbsPublic.json', '.'),
        ('currentArbsWebull.json', '.'),
        ('currentArbsFirstrade.json', '.'),
        ('currentArbsTradier.json', '.'),
        ('currentArbsFennel.json', '.'),
        ('market_holidays.json', '.')
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='rab',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep the console window open
    icon='rab.ico'  # Optional: include if you have a custom icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='rab'
)
