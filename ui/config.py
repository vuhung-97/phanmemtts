from __future__ import annotations

import json
from pathlib import Path

from core.paths import app_dir, data_dir

_BASE_DIR = app_dir()
CONFIG_PATH = _BASE_DIR / "models" / "voice_config.json"
TEST_TEXT_PATH = _BASE_DIR / "models" / "test_text.json"

# Cau hinh chung (precision / threads / cach luu audio) -> thu muc du lieu nguoi dung.
SETTINGS_PATH = data_dir() / "app_settings.json"

DEFAULT_TEST_TEXT = "Tôi là giọng đọc AI của Lữ đoàn 170 - Vùng 1 Hải quân"

# Gia tri mac dinh cho tung muc cai dat.
DEFAULT_SETTINGS: dict = {
    "precision": "fp32",   # "fp32" | "int8"
    "threads": 0,          # 0 = tu dong, nguon dinh cua ONNX Runtime
    "storage": "auto",     # "auto" | "memory" | "disk"
    "gpu": False,          # dung backend PyTorch/CUDA neu co
}


def load_enabled_voices() -> set[str] | None:
    """Doc danh sach model_id duoc bat. None neu chua tung luu (bat tat ca)."""
    if not CONFIG_PATH.exists():
        return None
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return set(data.get("enabled", []))
    except (json.JSONDecodeError, OSError):
        return None


def save_enabled_voices(enabled: set[str]) -> None:
    """Ghi danh sach model_id duoc bat vao voice_config.json."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {"enabled": sorted(enabled)}
    CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_test_text() -> str:
    """Doc cau test tu test_text.json. Tra ve cau mac dinh neu chua co."""
    if not TEST_TEXT_PATH.exists():
        return DEFAULT_TEST_TEXT
    try:
        data = json.loads(TEST_TEXT_PATH.read_text(encoding="utf-8"))
        return str(data.get("text", DEFAULT_TEST_TEXT))
    except (json.JSONDecodeError, OSError):
        return DEFAULT_TEST_TEXT


def save_test_text(text: str) -> None:
    """Ghi cau test vao test_text.json."""
    TEST_TEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {"text": text.strip() or DEFAULT_TEST_TEXT}
    TEST_TEXT_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_settings() -> dict:
    """Doc cau hinh chung (ke gia tri mac dinh cho muc bi thieu)."""
    settings = dict(DEFAULT_SETTINGS)
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for key in DEFAULT_SETTINGS:
                    if key in data:
                        settings[key] = data[key]
        except (json.JSONDecodeError, OSError):
            pass
    return settings


def save_settings(settings: dict) -> None:
    """Ghi cau hinh chung xuong app_settings.json."""
    data = {k: settings.get(k, v) for k, v in DEFAULT_SETTINGS.items()}
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass
