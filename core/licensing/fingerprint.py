"""Nhận dạng máy: mã máy 10 ký tự + các giá trị bind/clone.

Bind key (6 byte)  = hash24(MachineGuid) + hash24(Volume serial ổ C:)
Phát hiện clone    = thêm 2 hash của CPU brand và mainboard (lưu trong license)

Vì sao 2 thành phần: MachineGuid và Volume serial là **duy nhất theo từng
máy**, còn tên CPU/mainboard trùng giữa các máy cùng model (không dùng để
sinh mã, chỉ dùng phát hiện clone).
"""

from __future__ import annotations

import hashlib
import os
import platform

from core.licensing import codec

MACHINE_CODE_LEN = 10
_BIND_SALT = b"PPMTTS|bind|v1|"
_FP_SALT = b"PPMTTS|fp|v1|"

_GUID_KEY = r"SOFTWARE\Microsoft\Cryptography"
_CPU_KEY = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
_BIOS_KEY = r"HARDWARE\DESCRIPTION\System\BIOS"

COMPONENT_ORDER = ("guid", "vol", "cpu", "board")

_cache: dict[str, int] | None = None


# ── Đọc giá trị thô ──

def _read_reg(path: str, name: str) -> str:
    if os.name != "nt":
        return ""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
            value, _ = winreg.QueryValueEx(key, name)
        return str(value)
    except Exception:
        return ""


def _volume_serial(root: str | None = None) -> str:
    if os.name != "nt":
        return ""
    root = root or (os.environ.get("SystemDrive", "C:") + "\\")
    try:
        import ctypes
        from ctypes import wintypes

        serial = wintypes.DWORD(0)
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root), None, 0, ctypes.byref(serial),
            None, None, None, 0,
        )
        if not ok:
            return ""
        return f"{serial.value:08X}"
    except Exception:
        return ""


def _board_value() -> str:
    parts = [
        _read_reg(_BIOS_KEY, "BaseBoardManufacturer"),
        _read_reg(_BIOS_KEY, "BaseBoardProduct"),
    ]
    if not any(part.strip() for part in parts):
        parts = [
            _read_reg(_BIOS_KEY, "SystemManufacturer"),
            _read_reg(_BIOS_KEY, "SystemProductName"),
            _read_reg(_BIOS_KEY, "BIOSVendor"),
            _read_reg(_BIOS_KEY, "BIOSVersion"),
        ]
    return " ".join(part for part in parts if part.strip())


def _norm(value: str) -> str:
    text = " ".join((value or "").strip().lower().split())
    return text or "UNKNOWN"


def read_components() -> dict[str, str]:
    """Đọc 4 thành phần thô (đã chuẩn hoá). Không cache — dùng cho chẩn đoán."""
    return {
        "guid": _norm(_read_reg(_GUID_KEY, "MachineGuid") or platform.node()),
        "vol": _norm(_volume_serial()),
        "cpu": _norm(_read_reg(_CPU_KEY, "ProcessorNameString")),
        "board": _norm(_board_value()),
    }


# ── Băm & sinh mã ──

def hash24(index: int, raw: str) -> int:
    digest = hashlib.sha256(
        _FP_SALT + str(index).encode() + b"|" + (raw or "").encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:3], "big")


def fp4_from(raw: dict[str, str]) -> dict[str, int]:
    """4 hash 24 bit: guid, vol (bind) + cpu, board (chống clone)."""
    return {name: hash24(i, raw.get(name, ""))
            for i, name in enumerate(COMPONENT_ORDER)}


def machine_bytes_from(fp: dict[str, int]) -> bytes:
    return fp["guid"].to_bytes(3, "big") + fp["vol"].to_bytes(3, "big")


def machine_code_from(fp: dict[str, int]) -> str:
    value = int.from_bytes(machine_bytes_from(fp), "big")
    return codec.encode_int(value, MACHINE_CODE_LEN)


def machine24_from_fp(fp: dict[str, int]) -> int:
    digest = hashlib.sha256(_BIND_SALT + machine_bytes_from(fp)).digest()
    return int.from_bytes(digest[:3], "big")


def parse_machine_code(code: str) -> bytes:
    """Giải mã mã máy 10 ký tự -> 6 byte. Sai -> ValueError."""
    value = codec.decode_text(code, MACHINE_CODE_LEN)
    if value >> 48:
        raise ValueError("Mã máy không hợp lệ")
    return value.to_bytes(6, "big")


def machine24_from_code(code: str) -> int:
    digest = hashlib.sha256(_BIND_SALT + parse_machine_code(code)).digest()
    return int.from_bytes(digest[:3], "big")


# ── API dùng trong app (có cache) ──

def fp4() -> dict[str, int]:
    global _cache
    if _cache is None:
        _cache = fp4_from(read_components())
    return dict(_cache)


def machine_code() -> str:
    return machine_code_from(fp4())


def machine24() -> int:
    return machine24_from_fp(fp4())


def format_machine_code(code: str | None = None) -> str:
    """Hiển thị 2 nhóm 5: 7K2QF-9M3XA."""
    return codec.group(code or machine_code(), 5)


def reset_cache() -> None:
    """Xoá cache (dùng cho test hoặc khi cần đọc lại phần cứng)."""
    global _cache
    _cache = None
