r"""Tiện ích dùng chung cho keygen GUI/CLI (chạy trên máy owner).

Hoạt động cả khi chạy từ repo lẫn khi đóng gói thành `KeygenTTS.exe`:
- Bản exe: secret + sổ key nằm trong `keys\` cạnh exe.
- Bản dev: dùng `tools\license_tool\keys\`.
- Có thể override bằng biến môi trường `PPMTTS_KEYGEN_DIR`,
  `PPMTTS_SECRET_FILE`, `PPMTTS_LEDGER`.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.licensing import codec, fingerprint, shortcode  # noqa: E402
from core.licensing.secret import derive_key, load_secret_file  # noqa: E402

KIND_CHOICES = {
    "7": shortcode.KIND_WEEK,
    "30": shortcode.KIND_MONTH,
    "lifetime": shortcode.KIND_LIFETIME,
    "custom": shortcode.KIND_CUSTOM,
}

SECRET_NAME = "license_secret.bin"
LEDGER_NAME = "issued.sqlite"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def base_dir() -> Path:
    """Thư mục gốc của tool (cạnh exe khi đóng gói, repo khi dev)."""
    env = os.environ.get("PPMTTS_KEYGEN_DIR")
    if env:
        return Path(env)
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return ROOT


def secret_path() -> Path:
    env = os.environ.get("PPMTTS_SECRET_FILE")
    if env:
        return Path(env)
    if is_frozen():
        return base_dir() / "keys" / SECRET_NAME
    return ROOT / "tools" / "license_tool" / "keys" / SECRET_NAME


def ledger_path() -> Path:
    env = os.environ.get("PPMTTS_LEDGER")
    if env:
        return Path(env)
    if is_frozen():
        return base_dir() / "keys" / LEDGER_NAME
    return ROOT / "tools" / "license_tool" / "keys" / LEDGER_NAME


def load_key(path: Path | None = None) -> bytes:
    """Đọc secret từ file và suy ra khoá HMAC."""
    return derive_key(load_secret_file(path or secret_path()))


def format_machine(text: str) -> str:
    """Chuẩn hoá + chia 2 nhóm 5: 7K2QF-9M3XA."""
    return codec.group(codec.normalize(text), 5)


def normalize_machine(text: str) -> str:
    """Lấy mã máy 10 ký tự từ chuỗi bất kỳ (kể cả tin nhắn có version)."""
    return fingerprint.extract_machine_code(text)


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
