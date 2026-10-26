"""Trạng thái bản quyền + điểm chặn.

`check_startup()` là nguồn duy nhất quyết định app có được dùng hay không.
Kết quả được cache 30 giây để không đọc registry mỗi lần bấm nút.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date

from core.licensing import fingerprint, shortcode, store, trial

# Trạng thái
LICENSED = "licensed"
TRIAL = "trial"
EXPIRED = "expired"
TRIAL_EXPIRED = "trial_expired"
MACHINE_MISMATCH = "machine_mismatch"
CLONE_DETECTED = "clone_detected"
CLOCK_ROLLBACK = "clock_rollback"
TAMPERED = "tampered"
RATE_LIMITED = "rate_limited"
NONE = "none"

ACTIVE_STATES = (LICENSED, TRIAL)

CLOCK_TOLERANCE = 3 * 86400      # cho phép lùi tối đa 3 ngày
CACHE_SECONDS = 30

_MESSAGES = {
    EXPIRED: "Mã kích hoạt đã hết hạn.",
    TRIAL_EXPIRED: "Đã hết 7 ngày dùng thử.",
    MACHINE_MISMATCH: "Mã này được cấp cho máy khác.",
    CLONE_DETECTED: "Bản cài đặt được kích hoạt trên máy khác. Vui lòng liên hệ để nhận mã mới.",
    CLOCK_ROLLBACK: "Đồng hồ máy đang bị lùi so với lần dùng trước. "
                    "Vui lòng chỉnh lại đồng hồ rồi mở lại ứng dụng.",
    TAMPERED: "Thông tin bản quyền bị thay đổi. Vui lòng kích hoạt lại.",
    NONE: "Thiết bị chưa được kích hoạt.",
}


@dataclass(frozen=True)
class LicenseStatus:
    state: str
    kind: int | None = None
    expiry: date | None = None
    days_left: int | None = None
    machine: str = ""
    message: str = ""

    @property
    def active(self) -> bool:
        return self.state in ACTIVE_STATES

    @property
    def is_trial(self) -> bool:
        return self.state == TRIAL

    @property
    def is_lifetime(self) -> bool:
        return self.state == LICENSED and self.kind == shortcode.KIND_LIFETIME

    def badge_text(self) -> str:
        if self.state == LICENSED:
            if self.is_lifetime:
                return "🔑 Vĩnh viễn"
            left = max(0, int(self.days_left or 0))
            return f"🔑 Còn {left} ngày"
        if self.state == TRIAL:
            left = max(0, int(self.days_left or 0))
            return f"🕐 Dùng thử: còn {left} ngày"
        if self.state in (EXPIRED, TRIAL_EXPIRED):
            return "⛔ Đã hết hạn"
        return "⚠ Chưa kích hoạt"


class LicenseError(Exception):
    def __init__(self, message: str, status: "LicenseStatus | None" = None) -> None:
        super().__init__(message)
        self.status = status


_cache: LicenseStatus | None = None
_cache_ts: float = 0.0


def _build(state: str, **kwargs) -> LicenseStatus:
    kwargs.setdefault("machine", fingerprint.format_machine_code())
    kwargs.setdefault("message", _MESSAGES.get(state, ""))
    return LicenseStatus(state=state, **kwargs)


def _evaluate(ts: float) -> LicenseStatus:
    machine = fingerprint.machine_code()
    machine24 = fingerprint.machine24()

    stored = store.load_license()
    if stored is not None and not store.license_valid(stored):
        return _build(TAMPERED)

    last = store.last_seen()
    if last and ts < last - CLOCK_TOLERANCE:
        return _build(CLOCK_ROLLBACK)

    if stored:
        return _evaluate_license(stored, machine, machine24, ts)

    info = trial.info(ts)
    if info.active:
        return _build(TRIAL, days_left=info.days_left)
    if info.expired:
        return _build(TRIAL_EXPIRED, days_left=0)
    return _build(NONE)


def _evaluate_license(stored: dict, machine: str, machine24: int,
                      ts: float) -> LicenseStatus:
    raw = str(stored.get("key") or "")
    try:
        code = shortcode.decode(raw)
    except shortcode.InvalidCode:
        return _build(TAMPERED)

    if code.machine24 != machine24:
        return _build(MACHINE_MISMATCH)

    current = fingerprint.fp4()
    saved = stored.get("fp4") or {}
    if (int(saved.get("guid", -1)) != current["guid"]
            or int(saved.get("vol", -1)) != current["vol"]):
        return _build(MACHINE_MISMATCH)

    cpu_changed = int(saved.get("cpu", -1)) != current["cpu"]
    board_changed = int(saved.get("board", -1)) != current["board"]
    if cpu_changed and board_changed:
        return _build(CLONE_DETECTED)
    if cpu_changed or board_changed:
        # Chỉ thay 1 linh kiện: cập nhật lại fp4 để lần sau không báo nữa.
        store.save_license(
            machine=str(stored.get("machine") or machine),
            key=raw,
            fp4=current,
            installed_at=int(stored.get("installed_at") or ts),
            max_seen_utc=max(int(stored.get("max_seen_utc") or 0), int(ts)),
        )

    today = shortcode.date_from_ts(ts)
    if code.is_expired(today):
        return _build(EXPIRED, kind=code.kind, expiry=code.expiry_date(),
                      days_left=0)
    return _build(LICENSED, kind=code.kind, expiry=code.expiry_date(),
                  days_left=code.days_left(today))


def check_startup(now: float | None = None,
                  use_cache: bool = True) -> LicenseStatus:
    global _cache, _cache_ts
    ts = float(now if now is not None else time.time())
    if use_cache and _cache is not None and 0 <= ts - _cache_ts <= CACHE_SECONDS:
        return _cache
    status = _evaluate(ts)
    _cache = status
    _cache_ts = ts
    return status


def assert_valid(now: float | None = None) -> LicenseStatus:
    status = check_startup(now)
    if not status.active:
        raise LicenseError(status.message or "Chưa kích hoạt", status)
    return status


def install(code_text: str, now: float | None = None) -> LicenseStatus:
    """Kích hoạt mã; lỗi -> LicenseError (kèm status để UI hiển thị)."""
    ts = float(now if now is not None else time.time())

    remaining = store.lock_remaining(ts)
    if remaining > 0:
        status = _build(RATE_LIMITED)
        raise LicenseError(
            f"Bạn đã nhập sai quá nhiều lần. Vui lòng thử lại sau {remaining} giây.",
            status,
        )

    try:
        code = shortcode.decode(code_text)
    except shortcode.InvalidCode:
        locked = store.register_failure(ts)
        status = _build(RATE_LIMITED if locked else TAMPERED)
        message = ("Mã kích hoạt không hợp lệ hoặc đã bị sửa. "
                   "Vui lòng kiểm tra lại.")
        if locked:
            message = f"Nhập sai quá nhiều lần. Vui lòng thử lại sau {locked} giây."
        raise LicenseError(message, status) from None

    machine24 = fingerprint.machine24()
    if code.machine24 != machine24:
        status = _build(MACHINE_MISMATCH)
        raise LicenseError(status.message, status)

    last = store.last_seen()
    if last and ts < last - CLOCK_TOLERANCE:
        status = _build(CLOCK_ROLLBACK)
        raise LicenseError(status.message, status)

    store.reset_failures()
    store.save_license(
        machine=fingerprint.machine_code(),
        key=shortcode.format_code(code_text),
        fp4=fingerprint.fp4(),
        installed_at=int(ts),
        max_seen_utc=max(int(last), int(ts)),
    )
    store.record_seen(ts)
    reset_cache()
    return check_startup(ts, use_cache=False)


def record_activity(now: float | None = None) -> LicenseStatus:
    """Gọi mỗi 60 giây trong app: ghi mốc thời gian + kiểm tra lại."""
    ts = float(now if now is not None else time.time())
    store.record_seen(ts)
    return check_startup(ts)


def reset_cache() -> None:
    global _cache, _cache_ts
    _cache = None
    _cache_ts = 0.0
