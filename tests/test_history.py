"""Kiểm thử core/history.py — lịch sử chỉ metadata, không sao chép audio."""

from __future__ import annotations

import json

from core.history import (
    MAX_ITEMS,
    MIGRATION_MARKER,
    HistoryStore,
    format_duration,
    format_size,
    make_preview,
)


def _make_audio(tmp_path, name: str, size: int):
    path = tmp_path / name
    path.write_bytes(b"\0" * size)
    return path


def test_add_stores_metadata_without_copy(tmp_path):
    root = tmp_path / "history"
    store = HistoryStore(root)
    source = _make_audio(tmp_path, "out.mp3", 2048)

    entry = store.add(source, voice="Giọng A", speed=1.25, duration=75.5,
                      chars=120, preview="Xin chào   các bạn")

    assert entry.size == 2048
    assert entry.preview == "Xin chào các bạn"
    assert entry.path == str(source.resolve())
    assert entry.exists is True
    assert source.exists()
    # Không tạo bản sao trong history/
    assert not (root / entry.id).exists()
    assert {p.name for p in root.iterdir()} == {"index.json", MIGRATION_MARKER}


def test_reload_keeps_path_and_metadata(tmp_path):
    root = tmp_path / "h"
    source = _make_audio(tmp_path, "a.mp3", 100)
    HistoryStore(root).add(source, voice="V", speed=1.5, duration=2.0,
                           chars=9, preview="abc")

    reloaded = HistoryStore(root)
    entry = reloaded.entries[0]
    assert entry.path == str(source.resolve())
    assert entry.voice == "V"
    assert entry.speed_text == "1.5x"
    assert reloaded.total_size() == 100


def test_missing_voice_becomes_empty(tmp_path):
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


def test_remove_does_not_delete_audio(tmp_path):
    root = tmp_path / "h"
    store = HistoryStore(root)
    source = _make_audio(tmp_path, "keep.mp3", 100)
    entry = store.add(source, voice="A")

    assert store.remove(entry.id) is True
    assert source.exists()
    assert store.entries == []
    assert store.remove("không-tồn-tại") is False


def test_clear_does_not_delete_audio(tmp_path):
    store = HistoryStore(tmp_path / "h")
    files = [_make_audio(tmp_path, f"c{i}.mp3", 50) for i in range(3)]
    for index, path in enumerate(files):
        store.add(path, voice=f"V{index}")

    assert store.clear() == 3
    assert store.entries == []
    assert store.total_size() == 0
    assert all(path.exists() for path in files)


def test_prune_by_item_count_keeps_files(tmp_path):
    store = HistoryStore(tmp_path / "h")
    files = [_make_audio(tmp_path, f"p{i}.mp3", 10) for i in range(5)]
    for index, path in enumerate(files):
        store.add(path, voice=f"V{index}")

    removed = store.prune(max_items=2)
    assert len(removed) == 3
    assert [e.voice for e in store.entries] == ["V4", "V3"]
    assert all(path.exists() for path in files)


def test_default_max_items_is_reasonable():
    assert MAX_ITEMS >= 50


def test_missing_file_is_flagged(tmp_path):
    store = HistoryStore(tmp_path / "h")
    source = _make_audio(tmp_path, "gone.mp3", 10)
    entry = store.add(source)
    source.unlink()
    assert entry.exists is False
    assert store.remove(entry.id) is True   # vẫn xoá được mục


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
            "path": str((tmp_path / "a.mp3").resolve()), "size": 10}
    (root / "index.json").write_text(
        json.dumps({"ver": 2, "entries": [good, {"id": "2"}]}),
        encoding="utf-8")
    (tmp_path / "a.mp3").write_bytes(b"\0")
    entries = HistoryStore(root).entries
    assert len(entries) == 1 and entries[0].voice == "A"


def test_legacy_copy_is_deleted_on_load(tmp_path):
    root = tmp_path / "h"
    folder = root / "old-id"
    folder.mkdir(parents=True)
    copy = folder / "audio.mp3"
    copy.write_bytes(b"\0" * 500)
    (root / "index.json").write_text(json.dumps([{
        "id": "old-id", "created_at": 1.0, "voice": "A", "speed": 1.0,
        "duration": 1.0, "chars": 1, "preview": "x",
        "audio_file": "old-id/audio.mp3", "size": 500,
    }]), encoding="utf-8")

    store = HistoryStore(root)
    assert store.entries == []
    assert not copy.exists()
    assert not folder.exists()
    assert store.migration_summary == (1, 500)
    assert (root / MIGRATION_MARKER).exists()


def test_legacy_file_outside_root_is_not_deleted(tmp_path):
    root = tmp_path / "h"
    root.mkdir()
    outside = tmp_path / "outside.mp3"
    outside.write_bytes(b"\0" * 10)
    (root / "index.json").write_text(json.dumps([{
        "id": "x", "created_at": 1.0, "audio_file": "../outside.mp3",
        "size": 10,
    }]), encoding="utf-8")

    store = HistoryStore(root)
    assert store.entries == []
    assert outside.exists()


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
