"""Mã kích hoạt 15 ký tự (75 bit) — sinh và xác thực.

Bố cục bit (MSB -> LSB):
    [74]      ver        1 bit   (1 = định dạng v1)
    [73..72]  kind       2 bit   (0=7 ngày, 1=30 ngày, 2=vĩnh viễn, 3=tuỳ chỉnh)
    [71..60]  expiry    12 bit   (số ngày kể từ 01/01/2026; kind=2 bỏ qua)
    [59..36]  machine24 24 bit   (bind theo MachineGuid + Volume serial)
    [35..0]   tag       36 bit   (HMAC-SHA256(secret, prefix) cắt ngắn)

Cùng (kind, expiry, máy) luôn cho cùng một mã — không có nonce.
"""

from __future__ import annotations

import hmac
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256

from core.licensing import codec
from core.licensing.secret import secret_key

CODE_LEN = 15
VER = 1
EPOCH = date(2026, 1, 1)
MAX_EXPIRY = 0xFFF          # 4095 ngày ~ 03/2038

KIND_WEEK = 0
KIND_MONTH = 1
KIND_LIFETIME = 2
KIND_CUSTOM = 3

KIND_DAYS = {KIND_WEEK: 7, KIND_MONTH: 30}
KIND_LABELS = {
    KIND_WEEK: "7 ngày",
    KIND_MONTH: "30 ngày",
    KIND_LIFETIME: "Vĩnh viễn",
    KIND_CUSTOM: "Tuỳ chỉnh",
}
MAX_CUSTOM_DAYS = 3650

_TAG_BITS = 36
_TAG_MASK = (1 << _TAG_BITS) - 1
_PREFIX_BITS = 39


class InvalidCode(ValueError):
    """Mã kích hoạt sai định dạng / sai chữ ký / không hỗ trợ."""


@dataclass(frozen=True)
class ShortCode:
    kind: int
    expiry_day: int
    machine24: int

    @property
    def is_lifetime(self) -> bool:
        return self.kind == KIND_LIFETIME

    @property
    def label(self) -> str:
        return KIND_LABELS.get(self.kind, "Không rõ")

    def expiry_date(self) -> date | None:
        if self.is_lifetime:
            return None
        return EPOCH + timedelta(days=self.expiry_day)

    def days_left(self, today: date | None = None) -> int | None:
        if self.is_lifetime:
            return None
        return self.expiry_day - day_index(today or utc_today())

    def is_expired(self, today: date | None = None) -> bool:
        if self.is_lifetime:
            return False
        return day_index(today or utc_today()) > self.expiry_day


def utc_today() -> date:
    return date_from_ts(time.time())


def date_from_ts(ts: float) -> date:
    """Ngày (UTC) tại mốc thời gian — dùng để kiểm tra hạn theo 'now' hiệu lực."""
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).date()


def day_index(day: date) -> int:
    return (day - EPOCH).days


def _tag(prefix: int, key: bytes | None = None) -> int:
    digest = hmac.new(key or secret_key(), prefix.to_bytes(5, "big"), sha256).digest()
    return int.from_bytes(digest[:5], "big") >> 4


def _build_prefix(kind: int, expiry_day: int, machine24: int) -> int:
    if not 0 <= machine24 <= 0xFFFFFF:
        raise ValueError("machine24 phải trong khoảng 0..16777215")
    if not 0 <= expiry_day <= MAX_EXPIRY:
        raise ValueError("Số ngày hết hạn vượt giới hạn (0..4095)")
    if kind not in KIND_LABELS:
        raise ValueError(f"Loại mã không hợp lệ: {kind}")
    return (VER << 38) | (kind << 36) | (expiry_day << 24) | machine24


def issue(machine24: int, kind: int, days: int | None = None,
          today: date | None = None, key: bytes | None = None) -> str:
    """Tạo mã kích hoạt 15 ký tự (đã chia 3 nhóm 5)."""
    base_day = day_index(today or utc_today())

    if kind == KIND_LIFETIME:
        expiry_day = 0
    elif kind in KIND_DAYS:
        expiry_day = base_day + KIND_DAYS[kind]
    elif kind == KIND_CUSTOM:
        if days is None:
            raise ValueError("Loại tuỳ chỉnh cần số ngày")
        if not 1 <= int(days) <= MAX_CUSTOM_DAYS:
            raise ValueError(f"Số ngày phải trong khoảng 1..{MAX_CUSTOM_DAYS}")
        expiry_day = base_day + int(days)
    else:
        raise ValueError(f"Loại mã không hợp lệ: {kind}")

    if kind != KIND_LIFETIME and expiry_day > MAX_EXPIRY:
        raise ValueError("Hạn vượt quá giới hạn định dạng (03/2038)")

    prefix = _build_prefix(kind, expiry_day, machine24)
    value = (prefix << _TAG_BITS) | _tag(prefix, key)
    return format_code(codec.encode_int(value, CODE_LEN))


def decode(code: str, key: bytes | None = None) -> ShortCode:
    """Giải mã + xác thực chữ ký. Sai -> InvalidCode."""
    try:
        value = codec.decode_text(code, CODE_LEN)
    except ValueError as exc:
        raise InvalidCode(str(exc)) from None

    prefix = value >> _TAG_BITS
    tag = value & _TAG_MASK

    if prefix >> _PREFIX_BITS:
        raise InvalidCode("Mã kích hoạt không hợp lệ")

    ver = (prefix >> 38) & 0x1
    if ver != VER:
        raise InvalidCode("Phiên bản mã kích hoạt không được hỗ trợ")

    expected = _tag(prefix, key)
    if not hmac.compare_digest(expected.to_bytes(5, "big"), tag.to_bytes(5, "big")):
        raise InvalidCode("Mã kích hoạt không hợp lệ hoặc đã bị sửa")

    kind = (prefix >> 36) & 0x3
    expiry_day = (prefix >> 24) & 0xFFF
    machine24 = prefix & 0xFFFFFF
    if kind not in KIND_LABELS:
        raise InvalidCode("Loại mã không hợp lệ")
    if kind != KIND_LIFETIME and expiry_day == 0:
        raise InvalidCode("Hạn dùng không hợp lệ")

    return ShortCode(kind=kind, expiry_day=expiry_day, machine24=machine24)


def format_code(code: str) -> str:
    """Chia 15 ký tự thành 3 nhóm 5: 7K2QF-9M3XA-B8T1Z."""
    return codec.group(codec.normalize(code), 5)
