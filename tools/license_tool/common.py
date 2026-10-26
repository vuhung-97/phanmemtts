"""Tiện ích dùng chung cho keygen GUI và CLI (chạy trên máy owner)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# Cho phép chạy trực tiếp từ tools/license_tool/ (sys.path[0] là thư mục script).
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.licensing import codec, fingerprint, shortcode  # noqa: E402
from core.licensing.secret import (SECRET_PATH, derive_key,  # noqa: E402
                                   load_secret_file)

KIND_CHOICES = {
    "7": shortcode.KIND_WEEK,
    "30": shortcode.KIND_MONTH,
    "lifetime": shortcode.KIND_LIFETIME,
    "custom": shortcode.KIND_CUSTOM,
}


def load_key(path: Path | None = None) -> bytes:
    """Đọc secret từ file và suy ra khoá HMAC."""
    return derive_key(load_secret_file(path))


def format_machine(text: str) -> str:
    """Chuẩn hoá + chia 2 nhóm 5: 7K2QF-9M3XA."""
    return codec.group(codec.normalize(text), 5)


def normalize_machine(text: str) -> str:
    """Chuẩn hoá mã máy, raise ValueError nếu không hợp lệ."""
    cleaned = codec.normalize(text)
    if len(cleaned) != fingerprint.MACHINE_CODE_LEN:
        raise ValueError(
            f"Mã máy phải có đúng {fingerprint.MACHINE_CODE_LEN} ký tự "
            f"(đang {len(cleaned)})")
    fingerprint.parse_machine_code(cleaned)
    return cleaned


def create_code(machine: str, kind: int, days: int | None = None,
                key: bytes | None = None,
                today: date | None = None) -> tuple[str, shortcode.ShortCode]:
    """Tạo mã kích hoạt + trả kèm thông tin đã giải mã."""
    normalized = normalize_machine(machine)
    machine24 = fingerprint.machine24_from_code(normalized)
    if key is None:
        key = load_key()
    code = shortcode.issue(machine24, kind, days=days, key=key, today=today)
    return code, shortcode.decode(code, key=key)


def expiry_text(sc: shortcode.ShortCode) -> str:
    if sc.is_lifetime:
        return "Vĩnh viễn"
    expiry = sc.expiry_date()
    return expiry.strftime("%d/%m/%Y") if expiry else "—"


def kind_text(kind: int, days: int | None = None) -> str:
    if kind == shortcode.KIND_CUSTOM:
        return f"Tuỳ chỉnh {days} ngày" if days else "Tuỳ chỉnh"
    return shortcode.KIND_LABELS.get(kind, "—")
