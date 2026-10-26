# -*- mode: python ; coding: utf-8 -*-
# KeygenTTS — tool cấp mã kích hoạt, đóng gói one-file.
# Chỉ gồm tkinter + core.licensing + tools/license_tool; KHÔNG kèm thư viện AI.
#
# Build:  build_keygen.bat
# Output: dist\KeygenTTS\KeygenTTS.exe (+ keys\license_secret.bin)

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parents[1]
TOOL_DIR = ROOT / "tools" / "license_tool"
ICON = ROOT / "build" / "keygen.ico"

block_cipher = None

a = Analysis(
    [str(TOOL_DIR / "keygen.pyw")],
    pathex=[str(ROOT), str(TOOL_DIR)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Thư viện của app chính — không cần cho tool
        "numpy", "scipy", "torch", "torchaudio", "vieneu", "vieneu_utils",
        "sea_g2p", "customtkinter", "PIL", "pandas", "matplotlib", "docx",
        "onnxruntime", "soundfile", "sounddevice", "huggingface_hub",
        "engine", "audio", "ui", "packaging", "tests", "pytest",
        "tkinter.test",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="KeygenTTS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON) if ICON.is_file() else None,
)
