"""Ghép 4 mảnh secret thành khoá ký HMAC cho mã kích hoạt.

Bản trong repo dùng mảnh giả (dev/test). Bản phát hành được build từ cây
source tạm đã chạy `tools/inject_secret.py` để thay 4 mảnh thật.

K = SHA-256(b"PPMTTS|key|v1|" + mảnh1 + mảnh2 + mảnh3 + mảnh4)
"""

from __future__ import annotations

import hashlib

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

_CACHE: bytes | None = None


def secret_key() -> bytes:
    """Khoá 32 byte dùng cho HMAC-SHA256 của mã kích hoạt."""
    global _CACHE
    if _CACHE is None:
        _CACHE = hashlib.sha256(b"PPMTTS|key|v1|" + b"".join(_PARTS)).digest()
    return _CACHE


def secret_fingerprint() -> str:
    """16 hex đầu của SHA-256(K) — so 2 bản build mà không lộ khoá."""
    return hashlib.sha256(secret_key()).hexdigest()[:16]


def is_placeholder() -> bool:
    """True khi đang dùng mảnh giả trong repo (build dev)."""
    return _PARTS == _PLACEHOLDER
