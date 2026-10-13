from __future__ import annotations

import json
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = _BASE_DIR / "models" / "voice_config.json"
TEST_TEXT_PATH = _BASE_DIR / "models" / "test_text.json"

DEFAULT_TEST_TEXT = "Tôi là giọng đọc AI của Lữ đoàn 170 - Vùng 1 Hải quân"


def load_enabled_voices() -> set[str] | None:
    """Đọc danh sách model_id được bật. None nếu chưa từng lưu (bật tất cả)."""
    if not CONFIG_PATH.exists():
        return None
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return set(data.get("enabled", []))
    except (json.JSONDecodeError, OSError):
        return None


def save_enabled_voices(enabled: set[str]) -> None:
    """Ghi danh sách model_id được bật vào voice_config.json."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {"enabled": sorted(enabled)}
    CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_test_text() -> str:
    """Đọc câu test từ test_text.json. Trả về câu mặc định nếu chưa có."""
    if not TEST_TEXT_PATH.exists():
        return DEFAULT_TEST_TEXT
    try:
        data = json.loads(TEST_TEXT_PATH.read_text(encoding="utf-8"))
        return str(data.get("text", DEFAULT_TEST_TEXT))
    except (json.JSONDecodeError, OSError):
        return DEFAULT_TEST_TEXT


def save_test_text(text: str) -> None:
    """Ghi câu test vào test_text.json."""
    TEST_TEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {"text": text.strip() or DEFAULT_TEST_TEXT}
    TEST_TEXT_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
