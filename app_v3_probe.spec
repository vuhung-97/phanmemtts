# -*- mode: python ; coding: utf-8 -*-
# PROBE đóng gói (console=True) — cùng cấu hình với app_v3.spec nhưng chạy
# headless để kiểm tra đường TTS trong môi trường frozen (nạp model, tổng hợp,
# xuất MP3). KHÔNG dùng để phát hành — chỉ dùng test.
# Build: .venv\Scripts\python.exe -m PyInstaller --clean --noconfirm app_v3_probe.spec

block_cipher = None

from PyInstaller.utils.hooks import collect_submodules as _collect_submodules
from PyInstaller.utils.hooks import collect_data_files as _collect_data_files


def _safe_submodules(pkg):
    try:
        mods = _collect_submodules(pkg)
    except Exception:
        return []
    return [m for m in mods if '.tests' not in m and '.test' not in m and 'f2py' not in m]


def _safe_data(pkg):
    try:
        return list(_collect_data_files(pkg))
    except Exception:
        return []


_NUMPY_HIDDEN = _safe_submodules('numpy')
_SCIPY_HIDDEN = _safe_submodules('scipy')
_EXTRA_DATA = _safe_data('vieneu') + _safe_data('sea_g2p')

a = Analysis(
    ['packaging/probe_entry.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('logo/logo.jpg', 'logo'),
        ('models/vieneu/voice.json', 'models/vieneu'),
        ('models/vieneu/custom_voices.json', 'models/vieneu'),
        ('models/voice_config.json', 'models'),
        ('models/test_text.json', 'models'),
    ] + _EXTRA_DATA,
    hiddenimports=[
        'vieneu',
        'vieneu_utils',
        'onnxruntime',
        'sounddevice',
        'soundfile',
        'scipy.special._cdflib',
        'scipy.signal',
        'numpy',
        'numpy._core._exceptions',
        'scipy._external.array_api_compat.numpy.fft',
        'scipy._external.array_api_compat.common._fft',
        'docx',
        'num2words',
        'PIL',
        'customtkinter',
        'huggingface_hub',
    ] + _NUMPY_HIDDEN + _SCIPY_HIDDEN,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter.test', 'scipy.tests', 'numpy.tests'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AppV3_Probe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AppV3_Probe',
)
