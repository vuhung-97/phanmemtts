# -*- mode: python ; coding: utf-8 -*-
# BAN V2 MODULAR — EXE chi freeze main.py + thu vien ben thu ba.
# Code app (core/engine/audio/ui/version.py/main.py) NAM ROI dang .py
# canh EXE (copy sau build, xem HUONG DAN COPY ben duoi).
# Build: .venv\Scripts\python.exe -m PyInstaller app_v2.spec
# Output: dist/PhatThanhSo_V2/PhatThanhSo_V2.exe (OneDir)
# Sau build: copy source roi + models/ vao dist/PhatThanhSo_V2/
#   (xcopy core, engine, audio, ui, version.py, main.py — bo __pycache__)
#   + xcopy models (607MB hf_cache)
# Models KHONG bundle — copy tay nhu ban V1.
#
# LUU Y: neu sau nay them package moi (vd: video/) thi them ten vao
# `excludes` ben duoi VA vao danh sach copy.

block_cipher = None

# (giong app.spec) thu gom submodule numpy/scipy + data vieneu/sea_g2p
# TRUOC Analysis.
from PyInstaller.utils.hooks import collect_submodules as _collect_submodules
from PyInstaller.utils.hooks import collect_data_files as _collect_data_files


def _safe_submodules(pkg: str) -> list:
    try:
        mods = _collect_submodules(pkg)
    except Exception:
        return []
    return [m for m in mods if '.tests' not in m and '.test' not in m
            and 'f2py' not in m]


def _safe_data(pkg: str) -> list:
    try:
        return list(_collect_data_files(pkg))
    except Exception:
        return []


_NUMPY_HIDDEN = _safe_submodules('numpy')
_SCIPY_HIDDEN = _safe_submodules('scipy')
_EXTRA_DATA = _safe_data('vieneu') + _safe_data('sea_g2p')

a = Analysis(
    ['main.py'],
    pathex=[],
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
    runtime_hooks=['hooks/rthook_v2_syspath.py'],
    excludes=[
        'tkinter.test',
        'scipy.tests',
        'numpy.tests',
        # V2: loai code app khoi EXE — chay bang .py roi canh EXE.
        'core',
        'engine',
        'audio',
        'ui',
        'version',
        'selftest',
        'download_model',
    ],
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
    name='PhatThanhSo_V2',
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PhatThanhSo_V2',
)
