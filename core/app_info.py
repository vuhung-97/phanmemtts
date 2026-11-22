"""Tên ứng dụng đọc từ ``app_config.json`` để người dùng tự đổi được.

File được đặt cạnh ``.exe`` khi phát hành (hoặc ở thư mục gốc khi chạy source):

    {"app_name": "Tên phần mềm của bạn"}

Thiếu file / JSON lỗi / giá trị rỗng -> dùng tên mặc định trong ``version.py``.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import version
from core.paths import is_frozen

CONFIG_NAME = "app_config.json"
MAX_NAME_LEN = 120


def config_path() -> Path:
    """Vị trí file cấu hình: cạnh exe (bản đóng gói) hoặc gốc repo (dev)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent / CONFIG_NAME
    return Path(__file__).resolve().parents[1] / CONFIG_NAME


def _clean(value) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text:
        return None
    return text[:MAX_NAME_LEN]


def total_ram_gb() -> float:
    """Tổng RAM vật lý (GB). 0.0 nếu không đọc được (không chặn app)."""
    if sys.platform == "win32":
        try:
            import ctypes

            class _MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = _MemoryStatusEx()
            status.dwLength = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return float(status.ullTotalPhys) / (1024 ** 3)
        except Exception:
            return 0.0
        return 0.0
    try:
        return float(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")) \
            / (1024 ** 3)
    except (AttributeError, ValueError, OSError):
        return 0.0


def load_app_name(path: Path | str | None = None) -> str:
    """Trả tên app đã cấu hình, fallback về ``version.__app_name__``."""
    target = Path(path) if path is not None else config_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return version.__app_name__
    if not isinstance(data, dict):
        return version.__app_name__
    return _clean(data.get("app_name")) or version.__app_name__
