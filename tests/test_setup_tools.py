"""Kiểm thử tiện ích cài đặt: cửa sổ mạng, nhận diện INT8, thông báo lỗi."""

from __future__ import annotations

import os

import pytest

from engine import setup_tools
from engine.vieneu_engine import _friendly_load_error


def test_online_window_restores_state(monkeypatch):
    import huggingface_hub.constants as hf_constants

    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setattr(hf_constants, "HF_HUB_OFFLINE", True)

    with setup_tools.online_window():
        assert os.environ.get("HF_HUB_OFFLINE") == "0"
        assert hf_constants.HF_HUB_OFFLINE is False
        assert hf_constants.is_offline_mode() is False

    # Sau khi thoát -> trở lại trạng thái offline như cũ
    assert os.environ.get("HF_HUB_OFFLINE") == "1"
    assert hf_constants.HF_HUB_OFFLINE is True


def test_int8_installed_requires_all_files(tmp_path, monkeypatch):
    repo_dir = tmp_path / "models--pnnbao-ump--VieNeu-TTS-v3-Turbo" / "snapshots" / "abc"
    target = repo_dir / "onnx_int8"
    target.mkdir(parents=True)
    monkeypatch.setattr(setup_tools, "_cache_dir", lambda: tmp_path)

    assert setup_tools.int8_installed() is False      # thiếu hết file

    for name in setup_tools.INT8_FILES:
        (target / name).write_bytes(b"x")
    assert setup_tools.int8_installed() is True

    (target / setup_tools.INT8_FILES[0]).unlink()
    assert setup_tools.int8_installed() is False      # thiếu 1 file -> không dùng được


def test_friendly_error_for_missing_int8():
    raw = Exception(
        "An error happened while trying to locate the file on the Hub and we "
        "cannot find the requested files in the local cache. Please check your "
        "connection and try again or make sure your Internet connection is on."
    )
    err = _friendly_load_error(raw, "int8")
    assert isinstance(err, RuntimeError)
    assert "Chưa tải model INT8" in str(err)
    assert "Cài đặt" in str(err)


def test_friendly_error_keeps_other_errors():
    raw = RuntimeError("lỗi lạ khác")
    assert _friendly_load_error(raw, "int8") is raw
