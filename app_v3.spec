# -*- mode: python ; coding: utf-8 -*-
# BAN V3 — đóng gói OneDir, code app đóng gói trong EXE (giống app.spec).
# Build: .venv\Scripts\python.exe -m PyInstaller --clean app_v3.spec
# Output: dist/PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3/  (OneDir)
# Cấu trúc phát hành:
#   PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3.exe
#   _internal/                       (thư viện + logo, không chạm vào)
#   models/vieneu/hf_cache/          (model offline ~600MB — copy tay)
#   models/*.json                    (cấu hình giọng + giọng tùy chỉnh)
# Models 607MB KHÔNG bundle trong EXE -> copy tay models/ cạnh EXE
# (app_dir() khi frozen = thư mục chứa EXE, nên models/ phải nằm cạnh EXE).

block_cipher = None

# numpy 2.x lazy-import các module thuần-Python (vd: numpy._core._exceptions)
# mà phân tích tĩnh của PyInstaller không phát hiện -> thu gom toàn bộ
# submodule TRƯỚC Analysis rồi truyền vào hiddenimports.
# (append vào a.hiddenimports SAU Analysis không có tác dụng vì a.pure
# đã được tính xong.)
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
    # collect_data_files trả về list[(src, dest)] 2-tuple -> dùng trực tiếp
    # cho datas của Analysis (KHÁC với collect_all 3-tuple).
    try:
        return list(_collect_data_files(pkg))
    except Exception:
        return []


_NUMPY_HIDDEN = _safe_submodules('numpy')
_SCIPY_HIDDEN = _safe_submodules('scipy')
# Data bắt buộc runtime: vieneu/assets/*.json (preset voices),
# sea_g2p/sea_g2p.bin (G2P). Thiếu -> SDK rơi sang tải từ Hub -> báo lỗi mạng.
_EXTRA_DATA = _safe_data('vieneu') + _safe_data('sea_g2p')

APP_NAME = 'PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3'

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
        'matplotlib',
        'pandas',
        'IPython',
        'pytest',
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
    name=APP_NAME,
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
    name=APP_NAME,
)
