"""Lưu trạng thái bản quyền: license.json + .state + registry.

Ba nơi lưu cùng một mốc thời gian:
    %LOCALAPPDATA%\\PhanMemTTS\\license.json   (nguồn chính, có fp4)
    %LOCALAPPDATA%\\PhanMemTTS\\.state         (bản sao nhẹ)
    HKCU\\Software\\PhanMemTTS                 (sống sót khi xoá thư mục)

Chữ ký HMAC chỉ là chống sửa vô tình (khoá suy ra được từ mã máy), KHÔNG phải
bảo mật thật: hạn dùng luôn tính từ mã kích hoạt đã ký, không đọc từ JSON.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from pathlib import Path

from core.paths import data_dir
from core.licensing import fingerprint

REG_PATH = r"Software\PhanMemTTS"
LICENSE_FILE = "license.json"
STATE_FILE = ".state"

STATE_VER = 2
LOCK_THRESHOLD = 10       # số lần nhập sai
LOCK_WINDOW = 300         # trong 5 phút
LOCK_SECONDS = 60         # khoá 60 giây


class _Env:
    def __init__(self) -> None:
        self.base: Path = data_dir()
        self.registry: bool = True


_env = _Env()


def configure(base: Path | None = None, registry: bool = True) -> None:
    """Đổi nơi lưu (dùng cho test)."""
    _env.base = Path(base) if base is not None else data_dir()
    _env.registry = bool(registry)


def license_path() -> Path:
    return _env.base / LICENSE_FILE


def state_path() -> Path:
    return _env.base / STATE_FILE


def base_dir() -> Path:
    """Thư mục dữ liệu đang dùng (đổi được qua configure cho test)."""
    return _env.base


# ── Ký / kiểm chữ ký ──

def _state_key() -> bytes:
    return hashlib.sha256(
        b"PPMTTS|state|v2|" + fingerprint.machine_bytes_from(fingerprint.fp4())
    ).digest()


def _sign(canon: bytes) -> str:
    return hmac.new(_state_key(), canon, hashlib.sha256).hexdigest()


def _canon_license(data: dict) -> bytes:
    fp = data.get("fp4") or {}
    parts = [
        str(data.get("ver")),
        str(data.get("machine")),
        str(data.get("key")),
        f"{fp.get('guid')},{fp.get('vol')},{fp.get('cpu')},{fp.get('board')}",
        str(data.get("installed_at")),
        str(data.get("max_seen_utc")),
    ]
    return "|".join(parts).encode("utf-8")


def _canon_state(data: dict) -> bytes:
    parts = [
        str(data.get("ver")),
        str(data.get("last_seen") or 0),
        str(data.get("trial_start") or 0),
        str(data.get("fail_count") or 0),
        str(data.get("fail_window") or 0),
        str(data.get("lock_until") or 0),
    ]
    return "|".join(parts).encode("utf-8")


# ── JSON I/O ──

def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        os.replace(tmp, path)
        return True
    except OSError:
        return False


# ── Registry ──

def _reg_set(name: str, value: int | str) -> None:
    if not _env.registry or os.name != "nt":
        return
    try:
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
            if isinstance(value, int):
                winreg.SetValueEx(key, name, 0, winreg.REG_QWORD, int(value))
            else:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, str(value))
    except Exception:
        pass


def _reg_get(name: str, default: int = 0) -> int:
    if not _env.registry or os.name != "nt":
        return default
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
            value, _ = winreg.QueryValueEx(key, name)
        return int(value)
    except Exception:
        return default


# ── license.json ──

def load_license() -> dict | None:
    data = _read_json(license_path())
    return data or None


def license_valid(data: dict | None) -> bool:
    if not data:
        return False
    sig = str(data.get("state_sig") or "")
    if not sig:
        return False
    return hmac.compare_digest(sig, _sign(_canon_license(data)))


def save_license(machine: str, key: str, fp4: dict[str, int],
                 installed_at: int, max_seen_utc: int) -> dict:
    data = {
        "ver": STATE_VER,
        "machine": machine,
        "key": key,
        "fp4": {name: int(fp4.get(name, 0)) for name in fingerprint.COMPONENT_ORDER},
        "installed_at": int(installed_at),
        "max_seen_utc": int(max_seen_utc),
    }
    data["state_sig"] = _sign(_canon_license(data))
    _write_json(license_path(), data)
    return data


def touch_license(max_seen_utc: int) -> None:
    """Cập nhật mốc thời gian lớn nhất trong license.json (nếu có)."""
    data = load_license()
    if not data or not license_valid(data):
        return
    if int(data.get("max_seen_utc") or 0) >= max_seen_utc:
        return
    data["max_seen_utc"] = int(max_seen_utc)
    data["state_sig"] = _sign(_canon_license(data))
    _write_json(license_path(), data)


# ── .state ──

def load_state() -> dict:
    data = _read_json(state_path())
    if not data:
        return {}
    sig = str(data.get("state_sig") or "")
    if not sig or not hmac.compare_digest(sig, _sign(_canon_state(data))):
        return {}
    return data


def save_state(data: dict) -> bool:
    data = dict(data)
    data["ver"] = STATE_VER
    data["state_sig"] = _sign(_canon_state(data))
    return _write_json(state_path(), data)


# ── Mốc thời gian ──

def last_seen() -> int:
    """Mốc lớn nhất trong 3 nơi (0 nếu chưa có)."""
    values = [_reg_get("LastSeen", 0)]
    state = load_state()
    values.append(int(state.get("last_seen") or 0))
    data = load_license()
    if data and license_valid(data):
        values.append(int(data.get("max_seen_utc") or 0))
    return max(values)


def record_seen(now: float | None = None) -> int:
    """Ghi mốc hiện tại vào cả 3 nơi, không bao giờ ghi lùi."""
    ts = int(now if now is not None else time.time())
    current = last_seen()
    ts = max(ts, current)

    state = load_state()
    state["last_seen"] = ts
    save_state(state)
    _reg_set("LastSeen", ts)
    touch_license(ts)
    return ts


def trial_start() -> int | None:
    """Mốc bắt đầu dùng thử sớm nhất trong các nơi lưu."""
    values = []
    state = load_state()
    if state.get("trial_start"):
        values.append(int(state["trial_start"]))
    reg = _reg_get("TrialStart", 0)
    if reg:
        values.append(reg)
    data = load_license()
    if data and data.get("trial_start"):
        values.append(int(data["trial_start"]))
    return min(values) if values else None


def set_trial_start(ts: int) -> int:
    state = load_state()
    state["trial_start"] = int(ts)
    save_state(state)
    _reg_set("TrialStart", int(ts))
    return int(ts)


# ── Chống dò mã (rate limit) ──

def lock_remaining(now: float | None = None) -> int:
    ts = float(now if now is not None else time.time())
    state = load_state()
    lock_until = float(state.get("lock_until") or 0)
    return max(0, int(round(lock_until - ts)))


def is_locked(now: float | None = None) -> bool:
    return lock_remaining(now) > 0


def register_failure(now: float | None = None) -> int:
    """Ghi nhận 1 lần nhập sai; trả về số giây còn bị khoá (0 nếu chưa khoá)."""
    ts = float(now if now is not None else time.time())
    state = load_state()

    window = float(state.get("fail_window") or 0)
    count = int(state.get("fail_count") or 0)
    if ts - window > LOCK_WINDOW:
        window = ts
        count = 0

    count += 1
    lock_until = float(state.get("lock_until") or 0)
    if count >= LOCK_THRESHOLD:
        lock_until = ts + LOCK_SECONDS
        count = 0
        window = ts

    state["fail_count"] = count
    state["fail_window"] = int(window)
    state["lock_until"] = int(lock_until)
    save_state(state)
    return max(0, int(round(lock_until - ts)))


def reset_failures() -> None:
    state = load_state()
    state["fail_count"] = 0
    state["fail_window"] = 0
    state["lock_until"] = 0
    save_state(state)
