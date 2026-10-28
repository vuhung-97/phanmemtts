"""Kiểm thử cấu hình chung (app_settings.json) — gồm trạng thái điều khoản."""

from __future__ import annotations

import json

import ui.config as config


def test_defaults_include_terms(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "SETTINGS_PATH", tmp_path / "app_settings.json")
    settings = config.load_settings()
    assert settings["terms_accepted_at"] == 0
    assert settings["terms_version"] == 0
    assert settings["precision"] == "fp32"


def test_terms_are_persisted(monkeypatch, tmp_path):
    path = tmp_path / "app_settings.json"
    monkeypatch.setattr(config, "SETTINGS_PATH", path)
    settings = config.load_settings()
    settings["terms_accepted_at"] = 1793000000.0
    settings["terms_version"] = 1
    config.save_settings(settings)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["terms_version"] == 1
    again = config.load_settings()
    assert again["terms_accepted_at"] == 1793000000.0
    assert again["terms_version"] == 1


def test_unknown_keys_are_not_written(monkeypatch, tmp_path):
    path = tmp_path / "app_settings.json"
    monkeypatch.setattr(config, "SETTINGS_PATH", path)
    settings = config.load_settings()
    settings["khong_hop_le"] = True
    config.save_settings(settings)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "khong_hop_le" not in data


def test_corrupt_settings_fallback(monkeypatch, tmp_path):
    path = tmp_path / "app_settings.json"
    path.write_text("{ hỏng", encoding="utf-8")
    monkeypatch.setattr(config, "SETTINGS_PATH", path)
    settings = config.load_settings()
    assert settings["precision"] == "fp32"
    assert settings["terms_version"] == 0
