"""Dùng thử 7 ngày.

- Không tự bắt đầu: chỉ tính khi người dùng bấm "Dùng thử 7 ngày".
- Mốc bắt đầu lưu 3 nơi (license.json nếu có, .state, registry), lấy mốc sớm nhất.
- Nếu chưa có dấu vết dùng thử nhưng đã có dấu vết sử dụng app
  (app_settings.json / history / tmp) -> coi như đã dùng hết.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone

from core.licensing import store

TRIAL_DAYS = 7
DAY = 86400


@dataclass(frozen=True)
class TrialInfo:
    started: bool
    start_ts: int | None
    elapsed_days: int
    days_left: int
    expired: bool
    can_start: bool

    @property
    def active(self) -> bool:
        return self.started and not self.expired


def _elapsed(start_ts: int, now: float) -> int:
    start_day = datetime.fromtimestamp(int(start_ts), tz=timezone.utc).date()
    now_day = datetime.fromtimestamp(int(now), tz=timezone.utc).date()
    return max(0, (now_day - start_day).days)


def has_usage_traces() -> bool:
    """Đã từng dùng app chưa (dấu vết ngoài trial)."""
    base = store.base_dir()
    try:
        if (base / "app_settings.json").exists():
            return True
        history = base / "history"
        if history.is_dir() and any(history.iterdir()):
            return True
        tmp = base / "tmp"
        if tmp.is_dir() and any(tmp.iterdir()):
            return True
    except OSError:
        return False
    return False


def info(now: float | None = None) -> TrialInfo:
    ts = float(now if now is not None else time.time())
    start = store.trial_start()
    traces = has_usage_traces()

    if start is None:
        return TrialInfo(
            started=False,
            start_ts=None,
            elapsed_days=0,
            days_left=0,
            expired=False,
            can_start=not traces,
        )

    elapsed = _elapsed(start, ts)
    left = max(0, TRIAL_DAYS - elapsed)
    return TrialInfo(
        started=True,
        start_ts=start,
        elapsed_days=elapsed,
        days_left=left,
        expired=left <= 0,
        can_start=False,
    )


def start(now: float | None = None) -> TrialInfo:
    """Bắt đầu dùng thử; nếu đã bắt đầu trước đó thì trả trạng thái hiện tại."""
    ts = float(now if now is not None else time.time())
    if store.trial_start() is None:
        store.set_trial_start(int(ts))
        store.record_seen(ts)
    return info(ts)
