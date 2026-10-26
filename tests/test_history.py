"""Kiểm thử core/history.py — lịch sử bản dựng."""

from __future__ import annotations

import json

from core.history import (
    MAX_ITEMS,
    WARN_BYTES,
    HistoryStore,
    format_duration,
    format_size,
    make_preview,
)


def _make_audio(tmp_path, name: str, size: int):
    path = tmp_path / name
    path.write_bytes(b"\0" * size)
    return path


def test_add_copies_file_and_writes_index(tmp_path):
    root = tmp_path / "history"
    store = HistoryStore(root)
    source = _make_audio(tmp_path, "out.mp3", 2048)

    entry = store.add(source, voice="Giọng A", speed=1.25, duration=75.5,
                      chars=120, preview="Xin chào   các bạn")

    assert entry.size == 2048
    assert entry.preview == "Xin chào các bạn"
    assert (root / entry.audio_file).exists()
    # File gốc vẫn còn (chỉ sao chép, không di chuyển)
    assert source.exists()

    reloaded = HistoryStore(root)
    assert len(reloaded.entries) == 1
    assert reloaded.entries[0].voice == "Giọng A"
    assert reloaded.total_size() == 2048


def test_missing_voice_becomes_empty_string(tmp_path):
    store = HistoryStore(tmp_path / "h")
    entry = store.add(_make_audio(tmp_path, "nv.mp3", 10), voice=None)
    assert entry.voice == ""
    assert HistoryStore(tmp_path / "h").entries[0].voice == ""


def test_newest_entry_first(tmp_path):
    store = HistoryStore(tmp_path / "h")
    for i in range(3):
        store.add(_make_audio(tmp_path, f"a{i}.mp3", 10),
                  voice=f"V{i}", preview=f"câu {i}")
    assert [e.voice for e in store.entries] == ["V2", "V1", "V0"]


def test_remove_deletes_copy_but_not_user_file(tmp_path):
    store = HistoryStore(tmp_path / "h")
    source = _make_audio(tmp_path, "keep.mp3", 100)
    entry = store.add(source, voice="A")

    assert store.remove(entry.id) is True
    assert not (tmp_path / "h" / entry.audio_file).exists()
    assert source.exists()
    assert store.entries == []
    assert store.remove("không-tồn-tại") is False


def test_clear_removes_everything(tmp_path):
    store = HistoryStore(tmp_path / "h")
    for i in range(3):
        store.add(_make_audio(tmp_path, f"c{i}.mp3", 50), voice=f"V{i}")
    assert store.clear() == 3
    assert store.entries == []
    assert store.total_size() == 0


def test_prune_by_item_count(tmp_path):
    store = HistoryStore(tmp_path / "h")
    for i in range(5):
        store.add(_make_audio(tmp_path, f"p{i}.mp3", 10), voice=f"V{i}")
    removed = store.prune(max_items=2)
    assert len(removed) == 3
    assert len(store.entries) == 2
    assert [e.voice for e in store.entries] == ["V4", "V3"]
    for entry in store.entries:
        assert store.audio_path(entry).exists()


def test_prune_by_size_keeps_newest(tmp_path):
    store = HistoryStore(tmp_path / "h")
    for i in range(4):
        store.add(_make_audio(tmp_path, f"s{i}.mp3", 1000), voice=f"V{i}")
    store.prune(max_bytes=2500)
    assert len(store.entries) == 2
    assert [e.voice for e in store.entries] == ["V3", "V2"]


def test_missing_audio_folder_is_tolerated(tmp_path):
    store = HistoryStore(tmp_path / "h")
    entry = store.add(_make_audio(tmp_path, "gone.mp3", 10))
    (tmp_path / "h" / entry.id).rename(tmp_path / "h" / "moved")
    assert store.remove(entry.id) is True   # không ném lỗi


def test_corrupt_index_returns_empty(tmp_path):
    root = tmp_path / "h"
    root.mkdir()
    (root / "index.json").write_text("{ không phải json", encoding="utf-8")
    assert HistoryStore(root).entries == []


def test_index_tolerates_bad_entries(tmp_path):
    root = tmp_path / "h"
    root.mkdir()
    good = {"id": "1", "created_at": 1.0, "voice": "A", "speed": 1.0,
            "duration": 1.0, "chars": 1, "preview": "x",
            "audio_file": "1/audio.mp3", "size": 10}
    (root / "index.json").write_text(
        json.dumps([good, {"id": "2"}]), encoding="utf-8")
    entries = HistoryStore(root).entries
    assert len(entries) == 1 and entries[0].voice == "A"


def test_is_large_flag(tmp_path):
    store = HistoryStore(tmp_path / "h")
    store.add(_make_audio(tmp_path, "big.mp3", 10))
    assert store.is_large() is False
    store._entries[0].size = WARN_BYTES + 1
    assert store.is_large() is True


def test_default_max_items_is_reasonable():
    assert MAX_ITEMS >= 50


def test_format_helpers():
    assert format_size(512) == "512 B"
    assert format_size(2048) == "2 KB"
    assert format_size(5 * 1024 ** 2) == "5.0 MB"
    assert format_size(3 * 1024 ** 3) == "3.00 GB"
    assert format_duration(5) == "00:05"
    assert format_duration(75) == "01:15"
    assert format_duration(3675) == "1:01:15"


def test_make_preview_collapses_and_truncates():
    assert make_preview("  a \n b  ") == "a b"
    long_text = "x" * 200
    preview = make_preview(long_text, limit=20)
    assert len(preview) <= 20
    assert preview.endswith("…")
