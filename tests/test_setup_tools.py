"""Kiểm thử bộ cài offline: nhận diện INT8, kiểm tra file thiếu, thông báo lỗi."""

from __future__ import annotations

import os

from engine import setup_tools
from engine.vieneu_engine import _friendly_load_error

REPO_DIR = "models--pnnbao-ump--VieNeu-TTS-v3-Turbo"


def _make_bundle(tmp_path, precision: str = "fp32", root_files: bool = True):
    """Dựng cấu trúc models/vieneu/hf_cache giả trong tmp_path."""
    cache = tmp_path / "models" / "vieneu" / "hf_cache"
    snap = cache / REPO_DIR / "snapshots" / "abc123"
    for sub, names in (
        ("onnx_update", setup_tools.FP32_FILES),
        ("onnx_int8", setup_tools.INT8_FILES),
    ):
        folder = snap / sub
        folder.mkdir(parents=True, exist_ok=True)
        for name in names:
            (folder / name).write_bytes(b"x")
    if root_files:
        for name in setup_tools.ROOT_FILES:
            (snap / name).write_bytes(b"x")
    (cache.parent / "voice.json").write_text("{}", encoding="utf-8")
    return cache


def test_app_is_offline_by_default():
    import huggingface_hub.constants as hf_constants

    assert os.environ.get("HF_HUB_OFFLINE") == "1"
    assert hf_constants.HF_HUB_OFFLINE is True
    assert hf_constants.is_offline_mode() is True


def test_int8_installed_requires_all_files(tmp_path, monkeypatch):
    cache = _make_bundle(tmp_path)
    monkeypatch.setattr(setup_tools, "_cache_dir", lambda: cache)

    assert setup_tools.int8_installed() is True

    target = setup_tools.int8_dir()
    assert target is not None
    (target / setup_tools.INT8_FILES[0]).unlink()
    assert setup_tools.int8_installed() is False      # thiếu 1 file -> không dùng được


def test_verify_bundle_ok(tmp_path, monkeypatch):
    cache = _make_bundle(tmp_path)
    monkeypatch.setattr(setup_tools, "_cache_dir", lambda: cache)

    assert setup_tools.verify_bundle("fp32") == []
    assert setup_tools.verify_bundle("int8") == []
    assert setup_tools.bundle_ok() is True


def test_verify_bundle_detects_missing_files(tmp_path, monkeypatch):
    cache = _make_bundle(tmp_path)
    monkeypatch.setattr(setup_tools, "_cache_dir", lambda: cache)

    snap = next((cache / REPO_DIR / "snapshots").iterdir())
    (snap / "onnx_update" / "vieneu_backbone_shared.data").unlink()
    (snap / "speaker_encoder.onnx").unlink()

    missing = setup_tools.verify_bundle("fp32")
    assert "onnx_update/vieneu_backbone_shared.data" in missing
    assert "speaker_encoder.onnx" in missing
    assert setup_tools.bundle_ok() is False
    # Thiếu 1 câu model INT8 -> chỉ báo khi hỏi INT8
    snap2 = snap
    (snap2 / "onnx_int8" / setup_tools.INT8_FILES[0]).unlink()
    assert setup_tools.verify_bundle("fp32") == missing
    assert "onnx_int8/" + setup_tools.INT8_FILES[0] in setup_tools.verify_bundle("int8")


def test_verify_bundle_without_cache(tmp_path, monkeypatch):
    cache = tmp_path / "models" / "vieneu" / "hf_cache"
    monkeypatch.setattr(setup_tools, "_cache_dir", lambda: cache)

    missing = setup_tools.verify_bundle()
    assert any("onnx_update" in item for item in missing)
    assert "models/vieneu/voice.json" in missing


def test_friendly_error_for_missing_bundle(tmp_path, monkeypatch):
    cache = _make_bundle(tmp_path)
    monkeypatch.setattr(setup_tools, "_cache_dir", lambda: cache)
    snap = next((cache / REPO_DIR / "snapshots").iterdir())
    (snap / "onnx_int8" / "vieneu_prefill.onnx").unlink()

    raw = Exception(
        "An error happened while trying to locate the file on the Hub and we "
        "cannot find the requested files in the local cache. Please check your "
        "connection and try again or make sure your Internet connection is on."
    )
    err = _friendly_load_error(raw, "int8")
    assert isinstance(err, RuntimeError)
    assert "Bộ cài thiếu model (INT8)" in str(err)
    assert "onnx_int8/vieneu_prefill.onnx" in str(err)
    assert "models/" in str(err)


def test_friendly_error_keeps_other_errors():
    raw = RuntimeError("lỗi lạ khác")
    assert _friendly_load_error(raw, "fp32") is raw
