"""Kiểm thử lõi bản quyền: fingerprint, store, trial, guard."""

from __future__ import annotations

import json
import time
from datetime import date, timedelta

import pytest

from core.licensing import fingerprint, guard, shortcode, store, trial


@pytest.fixture()
def env(tmp_path):
    """Mỗi test dùng thư mục riêng, không ghi registry thật."""
    store.configure(tmp_path, registry=False)
    guard.reset_cache()
    yield tmp_path
    store.configure(None, registry=True)
    guard.reset_cache()


def _now() -> float:
    return time.time()


def _m24() -> int:
    return fingerprint.machine24()


def _code(kind: int = shortcode.KIND_MONTH, days: int | None = None,
          m24: int | None = None, today: date | None = None) -> str:
    return shortcode.issue(
        _m24() if m24 is None else m24, kind, days=days, today=today)


# ── Fingerprint ──

def test_machine_code_10_ky_tu(env):
    code = fingerprint.machine_code()
    assert len(code) == 10
    assert "-" not in code
    assert fingerprint.format_machine_code(code).count("-") == 1


def test_machine_code_on_dinh(env):
    assert fingerprint.machine_code() == fingerprint.machine_code()


def test_machine24_tu_ma_may(env):
    assert fingerprint.machine24_from_code(fingerprint.machine_code()) == _m24()


def test_parse_machine_code_sai(env):
    with pytest.raises(ValueError):
        fingerprint.parse_machine_code("ABC")


def test_fp4_hop_le(env):
    fp = fingerprint.fp4()
    assert set(fp) == {"guid", "vol", "cpu", "board"}
    assert all(0 <= v <= 0xFFFFFF for v in fp.values())
    assert len(fingerprint.machine_bytes_from(fp)) == 6


# ── Store ──

def test_save_load_license(env):
    code = _code()
    data = store.save_license(
        machine=fingerprint.machine_code(),
        key=shortcode.format_code(code),
        fp4=fingerprint.fp4(),
        installed_at=int(_now()),
        max_seen_utc=int(_now()),
    )
    assert store.license_path().exists()
    loaded = store.load_license()
    assert loaded is not None
    assert store.license_valid(loaded)
    assert loaded["key"] == data["key"]


def test_sua_key_bi_phat_hien(env):
    store.save_license(fingerprint.machine_code(), shortcode.format_code(_code()),
                       fingerprint.fp4(), int(_now()), int(_now()))
    path = store.license_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    data["key"] = shortcode.format_code(_code(shortcode.KIND_WEEK))
    path.write_text(json.dumps(data), encoding="utf-8")
    assert store.license_valid(store.load_license()) is False


def test_sua_max_seen_bi_phat_hien(env):
    store.save_license(fingerprint.machine_code(), shortcode.format_code(_code()),
                       fingerprint.fp4(), int(_now()), int(_now()))
    path = store.license_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    data["max_seen_utc"] = int(data["max_seen_utc"]) - 30 * 86400
    path.write_text(json.dumps(data), encoding="utf-8")
    assert store.license_valid(store.load_license()) is False


def test_trang_thai_chua_kich_hoat(env):
    status = guard.check_startup(_now())
    assert status.state == guard.NONE
    assert status.active is False


# ── Trial ──

def test_trial_bat_dau(env):
    now = _now()
    info = trial.start(now)
    assert info.active
    assert info.days_left == trial.TRIAL_DAYS

    status = guard.check_startup(now)
    assert status.state == guard.TRIAL
    assert status.days_left == 7
    assert "Dùng thử" in status.badge_text()


def test_trial_het_han(env):
    now = _now()
    store.set_trial_start(int(now - 8 * 86400))
    status = guard.check_startup(now)
    assert status.state == guard.TRIAL_EXPIRED
    assert status.active is False


def test_trial_khong_cho_bat_dau_khi_co_dau_vet(env):
    (env / "app_settings.json").write_text("{}", encoding="utf-8")
    info = trial.info(_now())
    assert info.can_start is False
    assert guard.check_startup(_now()).state == guard.NONE


def test_trial_giu_moc_da_co(env):
    now = int(_now())
    store.set_trial_start(now - 2 * 86400)
    info = trial.start(now)
    assert info.start_ts == now - 2 * 86400
    assert store.trial_start() == now - 2 * 86400


# ── Kích hoạt ──

def test_install_hop_le(env):
    now = _now()
    status = guard.install(_code(shortcode.KIND_MONTH), now=now)
    assert status.state == guard.LICENSED
    assert status.kind == shortcode.KIND_MONTH
    assert status.days_left in (29, 30)
    assert store.license_path().exists()


def test_install_vinh_vien(env):
    status = guard.install(_code(shortcode.KIND_LIFETIME), now=_now())
    assert status.state == guard.LICENSED
    assert status.is_lifetime
    assert status.badge_text() == "🔑 Vĩnh viễn"


def test_install_ma_may_khac(env):
    now = _now()
    code = _code(m24=_m24() ^ 0x1)
    with pytest.raises(guard.LicenseError) as exc:
        guard.install(code, now=now)
    assert "máy khác" in str(exc.value).lower()
    assert store.load_license() is None


def test_install_ma_sai_nhieu_lan_bi_khoa(env):
    now = _now()
    for _ in range(store.LOCK_THRESHOLD):
        with pytest.raises(guard.LicenseError):
            guard.install("AAAAA-AAAAA-AAAAA", now=now)

    assert store.is_locked(now)
    with pytest.raises(guard.LicenseError) as exc:
        guard.install(_code(), now=now)
    assert "thử lại sau" in str(exc.value).lower()


def test_install_ma_het_han(env):
    now = _now()
    code = _code(shortcode.KIND_MONTH, today=date.today() - timedelta(days=40))
    guard.install(code, now=now)
    guard.reset_cache()
    status = guard.check_startup(now)
    assert status.state == guard.EXPIRED
    assert status.active is False


def test_assert_valid(env):
    with pytest.raises(guard.LicenseError):
        guard.assert_valid(_now())
    guard.install(_code(), now=_now())
    assert guard.assert_valid(_now()).state == guard.LICENSED


# ── Chống clone ──

def _save_with_fp(now: float, **thay_doi) -> str:
    code = _code()
    fp = fingerprint.fp4()
    fp.update({k: v & 0xFFFFFF for k, v in thay_doi.items()})
    store.save_license(fingerprint.machine_code(), shortcode.format_code(code),
                       fp, int(now), int(now))
    guard.reset_cache()
    return code


def test_clone_khi_ca_cpu_va_board_khac(env):
    now = _now()
    fp = fingerprint.fp4()
    _save_with_fp(now, cpu=fp["cpu"] ^ 0xFFFF, board=fp["board"] ^ 0xFFFF)
    assert guard.check_startup(now).state == guard.CLONE_DETECTED


def test_doi_mot_linh_kien_thi_cap_nhat_fp4(env):
    now = _now()
    fp = fingerprint.fp4()
    _save_with_fp(now, cpu=fp["cpu"] ^ 0x1)
    assert guard.check_startup(now).state == guard.LICENSED
    assert store.load_license()["fp4"]["cpu"] == fp["cpu"]


# ── Đồng hồ ──

def test_lui_gio_qua_3_ngay_bi_chan(env):
    now = _now()
    guard.install(_code(), now=now)
    guard.reset_cache()
    status = guard.check_startup(now - 4 * 86400)
    assert status.state == guard.CLOCK_ROLLBACK
    assert status.active is False


def test_lui_gio_trong_dung_sai(env):
    now = _now()
    guard.install(_code(), now=now)
    guard.reset_cache()
    assert guard.check_startup(now - 2 * 86400).state == guard.LICENSED


def test_record_activity_cap_nhat_moc(env):
    now = _now()
    guard.install(_code(), now=now)
    guard.reset_cache()
    guard.record_activity(now + 120)
    assert store.last_seen() >= int(now + 120)
