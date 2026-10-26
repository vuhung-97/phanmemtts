"""Ghép 4 mảnh secret thành khoá ký HMAC cho mã kích hoạt.

Bản phát hành: `_k1..4.py` được tools/inject_secret.py ghi mảnh thật ngay
trước khi obfuscate → app không đọc file ngoài.

Bản dev (chạy từ source): nếu thấy `tools/license_tool/keys/license_secret.bin`
thì dùng luôn secret thật, để lập trình viên test được mã do keygen tạo.
Bản đã đóng gói (frozen) **bỏ qua** file này — chỉ dùng 4 mảnh đã inject.

K = SHA-256(b"PPMTTS|key|v1|" + 32 byte secret)
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from core.paths import is_frozen
from core.licensing import _k1, _k2, _k3, _k4

_PLACEHOLDER = (
    bytes.fromhex("0102030405060708"),
    bytes.fromhex("1112131415161718"),
    bytes.fromhex("2122232425262728"),
    bytes.fromhex("3132333435363738"),
)

_PARTS = (_k1.PART, _k2.PART, _k3.PART, _k4.PART)

if any(len(part) != 8 for part in _PARTS):
    raise RuntimeError("Mảnh secret không hợp lệ: mỗi mảnh phải đúng 8 byte.")

SECRET_LEN = 32
SECRET_PATH = (Path(__file__).resolve().parents[2] / "tools" / "license_tool"
               / "keys" / "license_secret.bin")

_CACHE: bytes | None = None


def derive_key(raw: bytes) -> bytes:
    """Khoá 32 byte dùng cho HMAC từ secret 32 byte."""
    if len(raw) != SECRET_LEN:
        raise ValueError(f"Secret phải đúng {SECRET_LEN} byte (đang {len(raw)})")
    return hashlib.sha256(b"PPMTTS|key|v1|" + raw).digest()


def load_secret_file(path: Path | None = None) -> bytes:
    """Đọc secret từ file (dùng cho keygen/CLI)."""
    target = Path(path) if path is not None else SECRET_PATH
    data = target.read_bytes()
    if len(data) != SECRET_LEN:
        raise ValueError(f"File secret không hợp lệ ({len(data)} byte): {target}")
    return data


def _dev_secret() -> bytes | None:
    """Secret thật khi chạy từ source (bản frozen bỏ qua)."""
    try:
        if is_frozen():
            return None
        data = SECRET_PATH.read_bytes()
    except Exception:
        return None
    return data if len(data) == SECRET_LEN else None


def secret_key() -> bytes:
    """Khoá 32 byte dùng cho HMAC-SHA256 của mã kích hoạt."""
    global _CACHE
    if _CACHE is None:
        raw = _dev_secret()
        if raw is not None:
            _CACHE = derive_key(raw)
        else:
            _CACHE = hashlib.sha256(
                b"PPMTTS|key|v1|" + b"".join(_PARTS)).digest()
    return _CACHE


def secret_fingerprint() -> str:
    """16 hex đầu của SHA-256(K) — so 2 bản build mà không lộ khoá."""
    return hashlib.sha256(secret_key()).hexdigest()[:16]


def is_placeholder() -> bool:
    """True khi không có secret thật (build dev từ repo sạch)."""
    if _dev_secret() is not None:
        return False
    return _PARTS == _PLACEHOLDER
