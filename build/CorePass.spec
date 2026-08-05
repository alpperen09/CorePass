# -*- mode: python ; coding: utf-8 -*-
# CorePass.exe için PyInstaller yapılandırması
# Derlemek için: pyinstaller build/CorePass.spec  (proje kök dizininden çalıştırın)

import sys
from pathlib import Path

block_cipher = None
APP_DIR = Path("app").resolve()

a = Analysis(
    [str(APP_DIR / "main.py")],
    pathex=[str(APP_DIR)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "customtkinter",
        "flask",
        "flask_cors",
        "cryptography",
        "cryptography.hazmat.primitives.kdf.pbkdf2",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="CorePass",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # Konsol penceresi olmadan çalışır (GUI uygulaması)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,               # Buraya "assets/corepass.ico" yolu verilebilir
)
