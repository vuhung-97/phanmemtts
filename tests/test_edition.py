"""Bản full: đã cấp sẵn bản quyền vĩnh viễn, không phụ thuộc store."""

from __future__ import annotations

from core.licensing import edition, guard, store


def test_full_edition_cap_vinh_vien(tmp_path, monkeypatch):
    store.configure(tmp_path, registry=False)
    monkeypatch.setattr(edition, "EDITION", edition.FULL)
    guard.reset_cache()

    status = guard.check_startup(use_cache=False)

    assert status.active
    assert status.state == guard.LICENSED
    assert status.is_lifetime
    assert status.badge_text() == "🔑 Vĩnh viễn"

    store.configure(None, registry=True)
    guard.reset_cache()


def test_full_edition_an_trang_ban_quyen(monkeypatch):
    monkeypatch.setattr(edition, "EDITION", edition.FULL)
    assert not edition.license_visible()
    monkeypatch.setattr(edition, "EDITION", edition.STANDARD)
    assert edition.license_visible()
