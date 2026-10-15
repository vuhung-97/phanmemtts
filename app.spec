# -*- mode: python ; coding: utf-8 -*-
# Build: .venv\Scripts\python.exe -m PyInstaller app.spec
# Output: dist/PhatThanhSo-MEDIA/PhatThanhSo-MEDIA.exe (OneDir)
# Models 607MB (hf_cache) KHONG bundle — copy tay models/ canh EXE.

block_cipher = None

# numpy 2.x lazy-import cac module thuan-Python (vd: numpy._core._exceptions)
# ma phan tich tinh cua PyInstaller khong phat hien -> thu gom toan bo
# submodule TRUOC Analysis va truyen vao hiddenimports.
# (append vao a.hiddenimports SAU Analysis khong co tac dung vi a.pure
# da duoc tinh xong.)
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
    # collect_data_files tra ve list[(src, dest)] 2-tuple -> dung truc tiep
    # cho datas cua Analysis (KHAC voi collect_all 3-tuple).
    try:
        return list(_collect_data_files(pkg))
    except Exception:
        return []


_NUMPY_HIDDEN = _safe_submodules('numpy')
_SCIPY_HIDDEN = _safe_submodules('scipy')
# Data bat buoc runtime: vieneu/assets/*.json (preset voices),
# sea_g2p/sea_g2p.bin (G2P). Thieu -> SDK roi sang tai tu Hub -> bao loi mang.
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
    runtime_hooks=[],
    excludes=[
        'tkinter.test',
        'scipy.tests',
        'numpy.tests',
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
    name='PhatThanhSo-MEDIA',
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
    name='PhatThanhSo-MEDIA',
)
