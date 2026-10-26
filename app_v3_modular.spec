# -*- mode: python ; coding: utf-8 -*-
# BAN V3 MODULAR — EXE chỉ freeze main.py + thư viện bên thứ ba.
# Code app (core/engine/audio/ui/version.py) NẰM RỜI cạnh EXE, đã obfuscate
# bằng PyArmor (xem build_v3.bat / plan_baomat.md).
#
# Build thử (không đụng bản phát hành trong dist/):
#   .venv\Scripts\python.exe -m PyInstaller --clean --noconfirm ^
#       --distpath build\dist_test --workpath build\pyi_test app_v3_modular.spec
#
# Sau build phải copy thêm vào cạnh EXE:
#   - core/ engine/ audio/ ui/ version.py  (bản đã obfuscate)
#   - pyarmor_runtime_000000/
#   - models/  (607MB hf_cache — chỉ lần build full)
#
# LƯU Ý: thêm package app mới (vd: video/) thì phải thêm tên vào `excludes`
# bên dưới VÀ vào danh sách copy của build_v3.bat.

block_cipher = None

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
    runtime_hooks=['hooks/rthook_v3_syspath.py'],
    excludes=[
        'tkinter.test',
        'scipy.tests',
        'numpy.tests',
        'matplotlib',
        'pandas',
        'IPython',
        'pytest',
        # Code app nằm rời cạnh EXE (đã obfuscate) — không nhúng vào PYZ.
        'core',
        'engine',
        'audio',
        'ui',
        'version',
        'tests',
        'packaging',
        'docs',
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
