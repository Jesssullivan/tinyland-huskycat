# -*- mode: python ; coding: utf-8 -*-


import os

# Get absolute path relative to spec file location
spec_root = os.path.abspath(SPECPATH)
src_path = os.path.join(spec_root, 'src')

a = Analysis(
    ['huskycat_main.py'],
    pathex=[],
    binaries=[],
    datas=[(src_path, 'src')],
    hiddenimports=['huskycat.core.factory', 'huskycat.core.base', 'huskycat.commands', 'huskycat.unified_validation', 'huskycat.gitlab_ci_validator', 'huskycat.mcp_server'],
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
    name='huskycat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
