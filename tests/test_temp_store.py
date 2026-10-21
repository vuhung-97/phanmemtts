"""Kiểm thử lưu âm thanh ra file tạm (chế độ đĩa cho bài dài)."""

from __future__ import annotations

import numpy as np

from audio.temp_store import TempAudioStore, TempSession, should_use_disk


def test_store_roundtrip(tmp_path):
    store = TempAudioStore(tmp_path / "a.pcm", 48000)
    data = np.array([0.0, 0.5, -0.5, 1.0, -1.0], dtype=np.float32)
    store.append(data)
    store.append(data)
    assert store.total_samples == 10

    out = store.read(0, 10)
    assert out.size == 10
    assert np.allclose(out, np.concatenate([data, data]), atol=1e-3)
    store.close()


def test_store_read_out_of_range(tmp_path):
    store = TempAudioStore(tmp_path / "b.pcm", 48000)
    store.append(np.ones(5, dtype=np.float32))
    assert store.read(10, 5).size == 0
    assert store.read(3, 100).size == 2
    store.close()


def test_cleanup_removes_file(tmp_path):
    path = tmp_path / "c.pcm"
    store = TempAudioStore(path, 48000)
    store.append(np.ones(5, dtype=np.float32))
    store.cleanup()
    assert not path.exists()


def test_session_creates_distinct_files(tmp_path):
    session = TempSession(tmp_path)
    s1 = session.store("play1", 48000)
    s2 = session.store("play2", 48000)
    s1.append(np.full(4, 0.25, dtype=np.float32))
    s2.append(np.full(4, 0.5, dtype=np.float32))
    assert s1.path != s2.path
    assert np.allclose(s1.read(0, 4), 0.25, atol=1e-3)
    assert np.allclose(s2.read(0, 4), 0.5, atol=1e-3)
    session.cleanup()
    assert not session.dir.exists()


def test_should_use_disk():
    assert should_use_disk("x" * 10, "disk") is True
    assert should_use_disk("x" * 10, "memory") is False
    assert should_use_disk("x" * 10, "auto") is False
    assert should_use_disk("x" * 30_000, "auto") is True


def test_read_does_not_disturb_writes(tmp_path):
    """Đọc (seek) không được làm lệch vị trí ghi — player đọc khi worker ghi."""
    store = TempAudioStore(tmp_path / "d.pcm", 48000)
    values = []
    for i in range(20):
        value = i / 20.0 - 0.5          # trong khoảng [-0.5, 0.45] (PCM16)
        values.append(value)
        store.append(np.full(100, value, dtype=np.float32))
        _ = store.read(0, 50)          # đọc xen kẽ như lúc phát
    store.flush()
    assert store.path.stat().st_size == 20 * 100 * 2
    # Đọc lại toàn bộ -> đúng thứ tự đã ghi
    out = store.read(0, store.total_samples)
    assert out.size == 2000
    assert np.allclose(out[100:200], values[1], atol=1e-3)
    assert np.allclose(out[-100:], values[19], atol=1e-3)
    store.close()
